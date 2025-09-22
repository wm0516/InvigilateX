from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from .backend import *
from .database import *
import calendar
from datetime import  datetime, time
from io import BytesIO
import pandas as pd
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
import traceback
import os
import re
import PyPDF2
from sqlalchemy import func


serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Handle Timeline Read From ExcelFile
# -------------------------------
def parse_date(val):
    if isinstance(val, datetime):
        return val.date()
    try:
        # Format from HTML5 input: "YYYY-MM-DD"
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.strptime(str(val), "%m/%d/%Y").date()
        except Exception:
            print(f"[Date Parse Error] Could not parse: {val}")
            return None

# -------------------------------
# Handle Timeline Read From ExcelFile And Convert To The Correct Format
# -------------------------------
def standardize_time_with_seconds(time_value):
    """
    Convert input time (string or datetime.time/datetime) to HH:MM:SS string format.
    """
    if isinstance(time_value, time):
        return time_value.strftime("%H:%M:%S")
    elif isinstance(time_value, datetime):
        return time_value.strftime("%H:%M:%S")
    elif isinstance(time_value, str):
        # Try multiple formats
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"):  # Handle 12-hour format with AM/PM
            try:
                dt = datetime.strptime(time_value.strip(), fmt)
                return dt.strftime("%H:%M:%S")  # Convert to 24-hour format (HH:MM:SS)
            except ValueError:
                continue
        print(f"[Time Parse Error] Could not parse: {time_value}")
        return None
    else:
        return None


# -------------------------------
# Read All InvigilatorAttendance Data From Database
# -------------------------------
def get_all_attendances():
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .all()
    )


# -------------------------------
# Calculate All InvigilatorAttendance and InvigilationReport Data From Database
# -------------------------------
def calculate_invigilation_stats():
    query = db.session.query(
        InvigilatorAttendance.attendanceId,
        InvigilatorAttendance.invigilatorId,
        InvigilatorAttendance.checkIn,
        InvigilatorAttendance.checkOut,
        Exam.examStartTime,
        Exam.examEndTime,
        InvigilatorAttendance.reportId
    ).join(Exam, Exam.examId == InvigilatorAttendance.reportId).all()

    total_report = len(set([row.reportId for row in db.session.query(InvigilatorAttendance.reportId).all()]))
    total_invigilator = len(set([row.invigilatorId for row in query]))

    stats = {
        "total_report": total_report,
        "total_invigilator": total_invigilator,
        "total_checkInOnTime": 0,
        "total_checkInLate": 0,
        "total_checkOutOnTime": 0,
        "total_checkOutEarly": 0,
        "total_checkInOut": 0,    # missing both
        "total_inProgress": 0     # checked in but no check out
    }

    for row in query:
        # Case 1: No checkIn at all
        if row.checkIn is None:
            stats["total_checkInOut"] += 1
            continue

        # Case 2: CheckIn exists, but no checkOut (in progress)
        if row.checkOut is None:
            stats["total_inProgress"] += 1
            continue

        # ✅ Both checkIn and checkOut exist
        if row.checkIn <= row.examStartTime:
            stats["total_checkInOnTime"] += 1
        else:
            stats["total_checkInLate"] += 1

        if row.checkOut >= row.examEndTime:
            stats["total_checkOutOnTime"] += 1
        else:
            stats["total_checkOutEarly"] += 1

    return stats


# -------------------------------
# Extract Base Name + Timestamp
# -------------------------------
def extract_base_name_and_timestamp(file_name):
    """Extract base name + optional _DDMMYY"""
    pattern = r"^(.*?)(?:_([0-9]{6}))(?:\s.*)?\.pdf$"
    match = re.match(pattern, file_name, re.IGNORECASE)

    if match:
        base_name = match.group(1).strip()
        timestamp_str = match.group(2)
        try:
            timestamp = datetime.strptime(timestamp_str, "%d%m%y")
        except ValueError:
            timestamp = None
    else:
        base_name = re.sub(r"(_\d{6}.*)?\.pdf$", "", file_name, flags=re.IGNORECASE).strip()
        timestamp = None

    return base_name, timestamp

# -------------------------------
# Parse Activity Line
# -------------------------------
def parse_activity(line):
    activity = {}

    m_type = re.match(r"(LECTURE|TUTORIAL|PRACTICAL)", line)
    if m_type:
        activity["class_type"] = m_type.group(1)

    m_time = re.search(r",(\d{2}:\d{2}-\d{2}:\d{2})", line)
    if m_time:
        activity["time"] = m_time.group(1)

    m_weeks = re.search(r"WEEKS:([^C]+)", line)
    if m_weeks:
        weeks_data = m_weeks.group(1).split(",")
        if len(weeks_data) > 1:
            activity["weeks_range"] = weeks_data[:-1]
            activity["weeks_date"]  = weeks_data[-1]
        else:
            activity["weeks_range"] = weeks_data

    m_course = re.search(r"COURSES:([^;]+);", line)
    if m_course:
        activity["course"] = m_course.group(1)

    m_sections = re.search(r"SECTIONS:(.+?)ROOMS", line)
    if m_sections:
        sections = m_sections.group(1).strip(";").split(";")
        activity["sections"] = []
        for sec in sections:
            if "|" in sec:
                intake, code, sec_name = sec.split("|")
                activity["sections"].append({
                    "intake": intake,
                    "course_code": code,
                    "section": sec_name
                })

    m_room = re.search(r"ROOMS:([^;]+);", line)
    if m_room:
        activity["room"] = m_room.group(1)

    return activity


# -------------------------------
# Parse Timetable Text
# -------------------------------
def parse_timetable(raw_text):
    text_no_whitespace = re.sub(r"\s+", "", raw_text)

    lecturer_name = "UNKNOWN"
    timerow = ""

    # Try extract title/timerow
    title_match = re.match(r"^(.*?)(07:00.*?23:00)", text_no_whitespace)
    if title_match:
        title_raw   = title_match.group(1)
        timerow     = title_match.group(2)
    else:
        title_raw = ""

    # Extract lecturer name
    try:
        name_match = re.search(r"-([^-()]+)\(", title_raw)
        if name_match:
            raw_name            = name_match.group(1)
            formatted_name      = re.sub(r'(?<!^)([A-Z])', r' \1', raw_name).strip()
            formatted_name      = formatted_name.replace("A/ P", "A/P").replace("A/ L", "A/L")
            lecturer_name       = formatted_name
            text_no_whitespace  = text_no_whitespace.replace(raw_name, lecturer_name.replace(" ", ""))
    except Exception:
        pass

    text = text_no_whitespace.upper()
    match_title = re.match(r"^(.*?)(07:00.*?23:00)", text)
    if match_title:
        title = match_title.group(1).strip()
        timerow = match_title.group(2).strip()
        text = text.replace(title, "").replace(timerow, "")
    else:
        title = "TIMETABLE"

    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for day in days:
        text = re.sub(day, f"\n\n{day}", text, flags=re.IGNORECASE)

    for kw in ["LECTURE", "TUTORIAL", "PRACTICAL", "PUBLISHED"]:
        sep = "\n\n" if kw == "PUBLISHED" else "\n"
        text = re.sub(kw, f"{sep}{kw}", text, flags=re.IGNORECASE)

    text = re.sub(r"\n{3,}", "\n\n", text)

    structured = {
        "title"     : title,
        "lecturer"  : lecturer_name,
        "timerow"   : timerow,
        "days"      : {}
    }

    current_day = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in days:
            current_day = line
            structured["days"][current_day] = []
        elif current_day and any(kw in line for kw in ["LECTURE", "TUTORIAL", "PRACTICAL"]):
            structured["days"][current_day].append(parse_activity(line))

    return structured

# -------------------------------
# Save Parsed Timetable to DB
# -------------------------------
def save_timetable_to_db(structured):
    new_entries = []
    lecturer = structured.get("lecturer")
    filename = structured.get("filename")

    for day, activities in structured["days"].items():
        for act in activities:
            if not (act.get("class_type") and act.get("time") and act.get("room") and act.get("course")):
                continue
            if act.get("sections"):
                for sec in act["sections"]:
                    if not (sec.get("intake") and sec.get("course_code") and sec.get("section")):
                        continue
                    new_entries.append({
                        "filename"      : filename,
                        "lecturerName"  : lecturer,
                        "classType"     : act.get("class_type"),
                        "classDay"      : day,
                        "classTime"     : act.get("time"),
                        "classRoom"     : act.get("room"),
                        "courseName"    : act.get("course"),
                        "courseIntake"  : sec.get("intake"),
                        "courseCode"    : sec.get("course_code"),
                        "courseSection" : sec.get("section"),
                        "classWeekRange": ",".join(act.get("weeks_range", [])) if act.get("weeks_range") else None,
                        "classWeekDate" : act.get("weeks_date"),
                    })

    # Bulk delete all rows for this lecturer before insert
    if lecturer:
        Timetable.query.filter_by(lecturerName=lecturer).delete()

    for entry in new_entries:
        db.session.add(Timetable(**entry))

    db.session.commit()
    return len(new_entries)


# -------------------------------
# Function handle file upload
# -------------------------------
def handle_file_upload(file_key, expected_cols, process_row_fn, redirect_endpoint, usecols="A:Z", skiprows=1):
    file = request.files.get(file_key)
    if file and file.filename:
        try:
            file_stream = BytesIO(file.read())
            excel_file = pd.ExcelFile(file_stream)

            records_added = 0
            records_failed = 0

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols=usecols,
                        skiprows=skiprows,
                        dtype=str
                    )
                    df.columns = [str(col).strip().lower() for col in df.columns]

                    if df.columns.tolist() != expected_cols:
                        raise ValueError(f"Excel columns do not match expected format: {df.columns.tolist()}")

                    # normalize all columns
                    for col in df.columns:
                        df[col] = df[col].apply(lambda x: str(x).strip() if isinstance(x, str) else x)

                    # process each row using the provided callback
                    for _, row in df.iterrows():
                        success, message = process_row_fn(row)
                        if success:
                            records_added += 1
                        else:
                            records_failed += 1

                except Exception as sheet_err:
                    print(f"[Sheet Error] {sheet_err}")

            if records_added > 0:
                flash(f"Successfully uploaded {records_added} record(s)", "success")
            if records_failed > 0:
                flash(f"Failed to upload {records_failed} record(s)", "error")
            if records_added == 0 and records_failed == 0:
                flash("No data uploaded", "error")

            return redirect(url_for(redirect_endpoint))

        except Exception as e:
            print(f"[File Processing Error] {e}")
            flash("File processing error: File upload in wrong format", "error")
            return redirect(url_for(redirect_endpoint))
    else:
        flash("No file uploaded", "error")
        return redirect(url_for(redirect_endpoint))


# -------------------------------
# Function for Admin ManageCourse Route Upload File
# -------------------------------
def process_course_row(row):
    return create_course_and_exam(
        department=str(row['department code']).strip(),
        code=str(row['course code']).strip(),
        section=str(row['course section']).strip(),
        name=str(row['course name']).strip(),
        hour=int(row['credit hour']),
        practical=str(row['practical lecturer']).strip().upper(),
        tutorial=str(row['tutorial lecturer']).strip().upper(),
        students=int(row['no of students'])
    )


# -------------------------------
# Function for Admin ManageExam Route Upload File
# -------------------------------
def process_exam_row(row):
    examDate_text = parse_date(row['date'])
    startTime_text = standardize_time_with_seconds(row['start'])
    endTime_text = standardize_time_with_seconds(row['end'])
    if not examDate_text or not startTime_text or not endTime_text:
        return False, "Invalid time/date"

    start_dt = datetime.combine(examDate_text, datetime.strptime(startTime_text, "%H:%M:%S").time())
    end_dt = datetime.combine(examDate_text, datetime.strptime(endTime_text, "%H:%M:%S").time())

    return create_exam_and_related(
        start_dt, end_dt,
        str(row['course/sec']).upper(),
        str(row['room']).upper(),
        str(row['lecturer']).upper(),
        None,
        invigilatorNo=0
    )


# -------------------------------
# Function for Admin ManageStaff Route Upload File, Validate Contact Number
# -------------------------------
def clean_contact(contact):
    if not contact:
        return ""
    contact = str(contact).strip().replace(".0", "")
    contact = "".join(filter(str.isdigit, contact))
    if contact and not contact.startswith("0"):
        contact = "0" + contact
    return contact if 10 <= len(contact) <= 11 else ""


# -------------------------------
# Function for Admin ManageStaff Route Upload File
# -------------------------------
def process_staff_row(row):
    role_mapping = {'lecturer': 1, 'hop': 2, 'dean': 3, 'admin': 4}
    hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')
    return create_staff(
        id=str(row['id']).upper(),
        department=str(row['department']).upper(),
        name=str(row['name']).upper(),
        role=role_mapping.get(str(row['role']).strip().lower()),
        email=str(row['email']),
        contact=clean_contact(row['contact']),
        gender=str(row['gender']).upper(),
        hashed_pw=hashed_pw
    )






# -------------------------------
# Read All LecturerName Under The Selected Department For ManageCoursePage
# -------------------------------
@app.route('/get_lecturers_by_department/<department_code>')
def get_lecturers_by_department(department_code):
    # Ensure case-insensitive match if needed
    print(f"User Department Code is: {department_code}")
    lecturers = User.query.filter_by(userDepartment=department_code, userLevel=1).all()
    lecturers_list = [{"userId": l.userId, "userName": l.userName} for l in lecturers]
    return jsonify(lecturers_list) 

# -------------------------------
# Read All CourseCodeSection Under The ManageCourseEditPage
# -------------------------------
@app.route('/get_courseCodeSection/<courseCodeSection_select>')
def get_courseCodeSection(courseCodeSection_select):
    course = Course.query.filter_by(courseCodeSection=courseCodeSection_select).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    course_data = {
        "courseCodeSection": course.courseCodeSection,
        "courseDepartment": course.courseDepartment,
        "courseCode": course.courseCodeSection.split('/')[0] if '/' in course.courseCodeSection else course.courseCodeSection,
        "courseSection": course.courseCodeSection.split('/')[1] if '/' in course.courseCodeSection else "",
        "coursePractical": course.coursePractical,
        "courseTutorial": course.courseTutorial,
        "courseName": course.courseName,
        "courseHour": course.courseHour,
        "courseStudent": course.courseStudent
    }
    return jsonify(course_data)


# -------------------------------
# Read All Course Under The Selected Department For ManageExamPage
# -------------------------------
@app.route('/get_courses_by_department/<department_code>')
def get_courses_by_department(department_code):
    courses = (
        Course.query
        .join(Exam)
        .filter(
            Course.courseDepartment == department_code,
            Exam.examStartTime.is_(None),
            Exam.examEndTime.is_(None)
        )
        .all()
    )

    course_list = [{"courseCodeSection": c.courseCodeSection} for c in courses]
    return jsonify(course_list)


# -------------------------------
# Read All CourseDetails Under The Selected Department For ManageExamPage
# -------------------------------
@app.route('/get_course_details/<program_code>/<path:course_code_section>')
def get_course_details(program_code, course_code_section):
    print(f"Requested: program_code={program_code}, course_code_section={course_code_section}")  # Optional debug
    selected_course = Course.query.filter_by(
        courseDepartment=program_code,
        courseCodeSection=course_code_section
    ).first()
    if selected_course:
        return jsonify({
            "practicalLecturer" : selected_course.coursePractical,
            "tutorialLecturer"  : selected_course.courseTutorial,
            "student"           : selected_course.courseStudent
        })
    return jsonify({"error": "Course not found"})


# -------------------------------
# Function for Admin ManageCourse Route
# -------------------------------
@app.route('/admin/manageCourse', methods=['GET', 'POST'])
def admin_manageCourse():
    try:
        # === Load basic data safely ===
        course_data = Course.query.all() or []
        department_data = Department.query.all() or []

        # === Dashboard numbers ===
        total_courses = Course.query.count() or 0
        courses_with_exams = Course.query.filter(Course.courseExamId.isnot(None)).count() or 0
        courses_without_exams = max(total_courses - courses_with_exams, 0)

        # Count rows with missing/empty values
        error_rows = Course.query.filter(
            (Course.courseDepartment.is_(None)) | (Course.courseDepartment == '') |
            (Course.courseCodeSection.is_(None)) | (Course.courseCodeSection == '') |
            (Course.courseName.is_(None)) | (Course.courseName == '') |
            (Course.courseHour.is_(None)) |
            (Course.courseStudent.is_(None)) |
            (Course.coursePractical.is_(None)) | (Course.coursePractical == '') |
            (Course.courseTutorial.is_(None)) | (Course.courseTutorial == '')
        ).count()

        # === Courses by department safely ===
        courses_by_department_raw = db.session.query(
            func.coalesce(Department.departmentCode, "Unknown"),
            func.count(Course.courseCodeSection)
        ).outerjoin(Course, Department.departmentCode == Course.courseDepartment
        ).group_by(func.coalesce(Department.departmentCode, "Unknown")
        ).having(func.count(Course.courseCodeSection) > 0
        ).order_by(func.coalesce(Department.departmentCode, "Unknown").asc()
        ).all() or []

        courses_by_department = [
            {"department": dept_code, "count": count}
            for dept_code, count in courses_by_department_raw
        ]

        # === POST Handling ===
        if request.method == 'POST':
            form_type = request.form.get('form_type')

            # --- Upload Section ---
            if form_type == 'upload':
                return handle_file_upload(
                    file_key='course_file',
                    expected_cols=['department code', 'course code', 'course section', 'course name', 'credit hour', 'practical lecturer', 'tutorial lecturer', 'no of students'],
                    process_row_fn=process_course_row,
                    redirect_endpoint='admin_manageCourse',
                    usecols="A:H"
                )

            # --- Edit Section ---
            elif form_type == 'edit':
                action = request.form.get('action')
                course_id = request.form.get('editCourseSelect')
                course = Course.query.get(course_id)
                if not course:
                    flash("Course not found", "error")
                    return redirect(url_for('admin_manageCourse'))

                if action == 'update':
                    course.courseDepartment = request.form.get('departmentCode', '').strip()
                    courseCode = request.form.get('courseCode', '').strip()
                    courseSection = request.form.get('courseSection', '').strip()
                    course.courseCodeSection = f"{courseCode}/{courseSection}"  
                    course.courseName = request.form.get('courseName', '').strip()
                    course.coursePractical = request.form.get('practicalLecturerSelect', '').strip()
                    course.courseTutorial = request.form.get('tutorialLecturerSelect', '').strip()

                    # Safe int conversion
                    try:
                        course.courseHour = int(request.form.get('courseHour', 0))
                    except (ValueError, TypeError):
                        course.courseHour = 0

                    try:
                        course.courseStudent = int(request.form.get('courseStudent', 0))
                    except (ValueError, TypeError):
                        course.courseStudent = 0

                    db.session.commit()
                    flash("Course updated successfully", "success")

                elif action == 'delete':
                    db.session.delete(course)
                    db.session.commit()
                    flash("Course deleted successfully", "success")

                return redirect(url_for('admin_manageCourse'))

            # --- Manual Add Section ---
            else:
                def safe_int(value, default=0):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return default

                form_data = {
                    "department": request.form.get('departmentCode', '').strip(),
                    "code": request.form.get('courseCode', '').replace(' ', ''),
                    "section": request.form.get('courseSection', '').replace(' ', ''),
                    "name": request.form.get('courseName', '').strip(),
                    "hour": safe_int(request.form.get('courseHour')),
                    "practical": request.form.get('practicalLecturerSelect', '').strip(),
                    "tutorial": request.form.get('tutorialLecturerSelect', '').strip(),
                    "students": safe_int(request.form.get('courseStudent')),
                }

                success, message = create_course_and_exam(**form_data)
                flash(message, "success" if success else "error")
                return redirect(url_for('admin_manageCourse'))

        # === GET Request ===
        return render_template(
            'admin/adminManageCourse.html',
            active_tab='admin_manageCoursetab',
            course_data=course_data,
            department_data=department_data,
            total_courses=total_courses,
            courses_with_exams=courses_with_exams,
            courses_without_exams=courses_without_exams,
            courses_by_department=courses_by_department,
            error_rows=error_rows
        )

    except Exception as e:
        # Show traceback in browser for debugging
        print(traceback.format_exc())
        return f"<pre>{traceback.format_exc()}</pre>", 500


# -------------------------------
# Function for Admin ManageDepartment Route
# -------------------------------
@app.route('/admin/manageDepartment', methods=['GET', 'POST'])
def admin_manageDepartment():
    department_data = Department.query.all()
    total_department = Department.query.count()
    department_with_dean = Department.query.filter(Department.deanId.isnot(None)).count()
    department_with_hop = Department.query.filter(Department.hopId.isnot(None)).count()

    # Get all currently assigned dean and hop IDs
    assigned_dean_ids = db.session.query(Department.deanId).filter(Department.deanId.isnot(None)).distinct()
    assigned_hop_ids = db.session.query(Department.hopId).filter(Department.hopId.isnot(None)).distinct()
    departmentCode = ''
    departmentName = ''
    deanId = ''
    hopId = ''

    # Exclude those already assigned
    dean_list = User.query.filter(User.userLevel == 2, ~User.userId.in_(assigned_dean_ids)).all()
    hop_list = User.query.filter(User.userLevel == 3, ~User.userId.in_(assigned_hop_ids)).all()
    
    # --------------------- MANUAL ADD DEPARTMENT FORM ---------------------
    if request.method == 'POST':
        departmentCode = request.form.get('departmentCode', '').strip().upper()
        departmentName = request.form.get('departmentName', '').strip().upper()
        deanId = request.form.get('deanName', '').strip().upper()
        hopId = request.form.get('hopName', '').strip().upper()

        dept = Department.query.filter_by(departmentCode=departmentCode, departmentName=departmentName).first()

        if dept:
            updated = False
            if deanId and not dept.deanId:
                dept.deanId = deanId
                updated = True
            if hopId and not dept.hopId:
                dept.hopId = hopId
                updated = True
            if updated:
                db.session.commit()
                flash("Department updated with new Dean and HOP", "success")
            else:
                flash("Department Code or Department Name already exists.", "error")
        else:
            # Check for conflicts
            if Department.query.filter_by(departmentCode=departmentCode).first():
                flash("Department Code already exists.", "error")
            elif Department.query.filter_by(departmentName=departmentName).first():
                flash("Department Name already exists.", "error")
            else:
                new_dept = Department(
                    departmentCode=departmentCode, 
                    departmentName=departmentName,
                    deanId=deanId if deanId else None,
                    hopId=hopId if hopId else None
                    )
                db.session.add(new_dept)
                db.session.commit()
                flash("New Department Added", "success")

        return redirect(url_for('admin_manageDepartment'))

    return render_template('admin/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', 
                           department_data=department_data, dean_list=dean_list, hop_list=hop_list, total_department=total_department,
                           department_with_hop=department_with_hop, department_with_dean=department_with_dean)


# -------------------------------
# Function for Admin ManageVenue Route
# -------------------------------
@app.route('/admin/manageVenue', methods=['GET', 'POST'])
def admin_manageVenue():
    if request.method == 'POST':
        venueNumber = request.form.get('venueNumber', '').strip().upper()
        venueFloor = request.form.get('venueFloor', '').strip()
        venueCapacity = request.form.get('venueCapacity', '').strip()
        venueStatus = request.form.get('venueStatus', '').strip()

        if Venue.query.filter_by(venueNumber=venueNumber).first():
            flash("Venue Room Already Exists", 'error')
        else:
            try:
                capacity = int(venueCapacity)
                if capacity < 0:
                    raise ValueError
                db.session.add(Venue(
                    venueNumber=venueNumber,
                    venueFloor=venueFloor,
                    venueCapacity=capacity,
                    venueStatus=venueStatus
                ))
                db.session.commit()
                flash("Venue Added", "success")
                return redirect(url_for('admin_manageVenue'))
            except ValueError:
                flash("Capacity must be a non-negative integer", 'error')

    # Always fetch latest data for display
    venue_data = Venue.query.all()
    total_venue = Venue.query.count()

    # Status counts
    counts = dict(
        db.session.query(Venue.venueStatus, func.count())
        .group_by(Venue.venueStatus)
        .all()
    )

    # Floor counts (no need to map manually, Jinja can unpack tuples)
    venues_by_floor = [
        {"floor": floor, "count": count}
        for floor, count in db.session.query(Venue.venueFloor, func.count())
        .group_by(Venue.venueFloor)
        .order_by(Venue.venueFloor)
        .all()
    ]

    return render_template(
        'admin/adminManageVenue.html',
        active_tab='admin_manageVenuetab',
        venue_data=venue_data,
        total_venue=total_venue,
        available=counts.get("AVAILABLE", 0),
        unavailable=counts.get("UNAVAILABLE", 0),
        in_service=counts.get("IN SERVICE", 0),
        venues_by_floor=venues_by_floor
    )


# -------------------------------
# Function for Admin ManageExam Route
# -------------------------------
@app.route('/admin/manageExam', methods=['GET', 'POST'])
def admin_manageExam():
    department_data = Department.query.all()
    venue_data = Venue.query.filter(Venue.venueStatus == 'AVAILABLE').all()
    exam_data = Exam.query.filter(
        Exam.examId.isnot(None),
        Exam.examStartTime.isnot(None),
        Exam.examEndTime.isnot(None)
    ).all()

    course_data = Course.query.join(Exam, Course.courseExamId == Exam.examId).filter(
        and_(
            Exam.examId.isnot(None),
            Exam.examStartTime.is_(None),
            Exam.examEndTime.is_(None)
        )
    ).all()

    total_exam = Exam.query.count()

    # Complete exams: all important columns are NOT NULL
    exam_with_complete = Exam.query.filter(
        Exam.examStartTime.isnot(None),
        Exam.examEndTime.isnot(None),
        Exam.examVenue.isnot(None),
        Exam.examNoInvigilator.isnot(None)
    ).count()

    # Error rows: completely empty or mostly NULL
    error_rows = Exam.query.filter(
        Exam.examStartTime.is_(None),
        Exam.examEndTime.is_(None),
        Exam.examVenue.is_(None),
        Exam.examNoInvigilator.is_(None)
    ).count()

    # Default manual form values
    courseSection_text = ''
    practicalLecturer_text = ''
    tutorialLecturer_text = ''
    venue_text = ''
    invigilatorNo_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # --------------------- UPLOAD ADD EXAM FORM ---------------------
        if form_type == 'upload':
            return handle_file_upload(
                file_key='exam_file',
                expected_cols=['date', 'day', 'start', 'end', 'program','course/sec', 'lecturer', 'no of', 'room'],
                process_row_fn=process_exam_row,
                redirect_endpoint='admin_manageExam',
                usecols="A:I"
            )

        # --------------------- DASHBOARD ADD EXAM FORM ---------------------
        elif form_type == 'dashboard':
            return redirect(url_for('admin_manageExam'))

        # --------------------- MANUAL ADD EXAM FORM ---------------------
        elif form_type == 'manual':
            try:
                startDate_raw = request.form.get('startDate', '').strip()
                endDate_raw = request.form.get('endDate', '').strip()
                startTime_raw = request.form.get('startTime', '').strip()
                endTime_raw = request.form.get('endTime', '').strip()

                if len(startTime_raw) == 5:
                    startTime_raw += ":00"
                if len(endTime_raw) == 5:
                    endTime_raw += ":00"

                start_dt = datetime.strptime(f"{startDate_raw} {startTime_raw}", "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(f"{endDate_raw} {endTime_raw}", "%Y-%m-%d %H:%M:%S")

                courseSection_text = request.form.get('courseSection', '').strip()
                venue_text = request.form.get('venue', '').strip()
                practicalLecturer_text = request.form.get('practicalLecturer', '').strip()
                tutorialLecturer_text = request.form.get('tutorialLecturer', '').strip()
                invigilatorNo_text = request.form.get('invigilatorNo', '0').strip()

                success, message = create_exam_and_related(
                    start_dt, end_dt, courseSection_text,
                    venue_text, practicalLecturer_text,
                    tutorialLecturer_text, invigilatorNo_text
                )

                if success:
                    flash(message, "success")
                else:
                    flash(message, "error")
                return redirect(url_for('admin_manageExam'))

            except Exception as manual_err:
                print(f"[Manual Form Error] {manual_err}")
                traceback.print_exc()
                flash(f"Error processing manual form: {manual_err}", "error")
                return redirect(url_for('admin_manageExam'))

    return render_template('admin/adminManageExam.html', active_tab='admin_manageExamtab', exam_data=exam_data, course_data=course_data, venue_data=venue_data, department_data=department_data,
                           total_exam=total_exam, exam_with_complete=exam_with_complete, error_rows=error_rows)


# -------------------------------
# Function for Admin ManageStaff Route
# -------------------------------
@app.route('/admin/manageStaff', methods=['GET', 'POST'])
def admin_manageStaff():
    user_data = User.query.all()
    department_data = Department.query.all()

    # === Dashboard Counts ===
    total_staff = User.query.count()

    # based on userLevel
    total_admin = User.query.filter_by(userLevel=4).count()
    total_lecturer = User.query.filter_by(userLevel=1).count()
    total_dean = User.query.filter_by(userLevel=2).count()
    total_hop = User.query.filter_by(userLevel=3).count()

    # based on gender
    total_male_staff = User.query.filter_by(userGender="MALE").count()
    total_female_staff = User.query.filter_by(userGender="FEMALE").count()

    # based on status (assuming: 1=activated, 0=deactivated)
    total_activated = User.query.filter_by(userStatus=1).count()
    total_deactivate = User.query.filter_by(userStatus=0).count()

    # incomplete rows check (e.g. NULL or empty important fields)
    error_rows = User.query.filter(
        (User.userDepartment.is_(None)) | (User.userDepartment == '') |
        (User.userName.is_(None)) | (User.userName == '') |
        (User.userEmail.is_(None)) | (User.userEmail == '') |
        (User.userContact.is_(None)) | (User.userContact == '') |
        (User.userGender.is_(None)) | (User.userGender == '') |
        (User.userLevel.is_(None))
    ).count()

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'upload':
            return handle_file_upload(
                file_key='staff_file',
                expected_cols=['id', 'name', 'department', 'role', 'email', 'contact', 'gender'],
                process_row_fn=process_staff_row,
                redirect_endpoint='admin_manageStaff',
                usecols="A:G"
            )

        elif form_type == 'modify':
            return redirect(url_for('admin_manageStaff'))

        elif form_type == 'manual':
            role_map = {"LECTURER": 1, "DEAN": 2, "HOP": 3, "ADMIN": 4}
            role_text = request.form.get('role', '').strip().upper()

            form_data = {
                "id": request.form.get('userid', '').strip(),
                "department": request.form.get('department', '').strip(),
                "name": request.form.get('username', '').strip(),
                "role": role_map.get(role_text, 0),  
                "email": request.form.get('email', '').strip(),
                "contact": request.form.get('contact', '').strip(),
                "gender": request.form.get('gender', '').strip(),
                "hashed_pw": bcrypt.generate_password_hash('Abc12345!').decode('utf-8'),
            }

            success, message = create_staff(**form_data)
            flash(message, "success" if success else "error")
            return redirect(url_for('admin_manageStaff'))

    return render_template(
        'admin/adminManageStaff.html',
        active_tab='admin_manageStafftab',
        user_data=user_data,
        department_data=department_data,
        total_staff=total_staff,
        total_admin=total_admin,
        total_hop=total_hop,
        total_Dean=total_dean,
        total_lecturer=total_lecturer,
        total_male_staff=total_male_staff,
        total_female_staff=total_female_staff,
        total_activated=total_activated,
        total_deactivate=total_deactivate,
        error_rows=error_rows
    )

# -------------------------------
# Function for Admin ManageLecturer Route
# -------------------------------
@app.route('/admin/manageTimetable', methods=['GET', 'POST'])
def admin_manageTimetable():
    # === Default data load ===
    timetable_data = Timetable.query.order_by(Timetable.timetableId.asc()).all()
    lecturers = sorted({row.lecturerName for row in timetable_data})
    selected_lecturer = request.args.get("lecturer")

    # Total timetable = total lecturers who have timetable saved
    total_timetable = db.session.query(Timetable.lecturerName).distinct().count()

    # Map day shortcodes to full keys for Jinja
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    day_counts = {
        f"{day.lower()}_timetable": Timetable.query.filter_by(classDay=day).count()
        for day in days
    }

    # === Handle POST (upload) ===
    if request.method == "POST":
        form_type = request.form.get('form_type')

        if form_type == 'upload':
            files = request.files.getlist("timetable_file[]")
            all_files = [file.filename for file in files]
            total_files_read = len(all_files)

            latest_files = {}
            skipped_files = []

            for file in files:
                base_name, timestamp = extract_base_name_and_timestamp(file.filename)
                if not base_name:
                    continue

                if base_name not in latest_files:
                    latest_files[base_name] = (timestamp, file)
                else:
                    existing_timestamp, existing_file = latest_files[base_name]
                    if timestamp and (existing_timestamp is None or timestamp > existing_timestamp):
                        skipped_files.append(existing_file.filename)
                        latest_files[base_name] = (timestamp, file)
                    else:
                        skipped_files.append(file.filename)

            filtered_filenames = [file.filename for (_, file) in latest_files.values()]
            total_files_filtered = len(filtered_filenames)

            results = []
            total_rows_inserted = 0
            selected_lecturer_name = None

            for base_name, (timestamp, file) in latest_files.items():
                reader = PyPDF2.PdfReader(file.stream)
                raw_text = "".join(page.extract_text() + " " for page in reader.pages if page.extract_text())

                structured = parse_timetable(raw_text)
                structured['filename'] = file.filename
                results.append(structured)

                rows_inserted = save_timetable_to_db(structured)
                total_rows_inserted += rows_inserted
                selected_lecturer_name = structured.get("lecturer")

            flash(f"✅ {total_rows_inserted} timetable rows updated successfully!", "success")

            # Refresh after upload
            timetable_data = Timetable.query.order_by(Timetable.timetableId.asc()).all()
            lecturers = sorted({row.lecturerName for row in timetable_data})
            total_timetable = db.session.query(Timetable.lecturerName).distinct().count()

            return render_template(
                'admin/adminManageTimetable.html',
                active_tab='admin_manageTimetabletab',
                timetable_data=timetable_data,
                results=results,
                selected_lecturer=selected_lecturer_name,
                lecturers=lecturers,
                upload_summary={
                    "total_files_uploaded": total_files_read,
                    "total_files_after_filter": total_files_filtered,
                    "files_after_filter": filtered_filenames
                },
                total_timetable=total_timetable,
                **day_counts
            )

    # ---- Default GET rendering ----
    return render_template(
        'admin/adminManageTimetable.html',
        active_tab='admin_manageTimetabletab',
        timetable_data=timetable_data,
        lecturers=lecturers,
        selected_lecturer=selected_lecturer,
        results=[],
        upload_summary=None,
        total_timetable=total_timetable,
        **day_counts
    )


# -------------------------------
# Function for Admin ManageInviglationTimetable Route
# -------------------------------
@app.route('/admin/manageInvigilationTimetable', methods=['GET', 'POST'])
def admin_manageInvigilationTimetable():
    attendances = get_all_attendances()
    stats = calculate_invigilation_stats()

    return render_template('admin/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', attendances=attendances, **stats)

# -------------------------------
# Function for Admin ManageInviglationReport Route
# -------------------------------
@app.route('/admin/manageInvigilationReport', methods=['GET', 'POST'])
def admin_manageInvigilationReport():
    attendances = get_all_attendances()
    stats = calculate_invigilation_stats()

    return render_template(
        'admin/adminManageInvigilationReport.html', active_tab='admin_manageInvigilationReporttab', attendances=attendances, **stats)



# -------------------------------
# Function for Admin ManageProfile Route
# -------------------------------
@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    adminId = session.get('user_id')
    admin = User.query.filter_by(userId=adminId).first()

    # Default values for GET requests
    admin_contact_text = admin.userContact if admin else ''
    admin_password1_text = ''
    admin_password2_text = ''
    
    # --------------------- MANUAL EDIT PROFILE FORM ---------------------
    if request.method == 'POST':
        admin_contact_text = request.form.get('contact', '').strip()
        admin_password1_text = request.form.get('password1', '').strip()
        admin_password2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(adminId, admin_contact_text, admin_password1_text, admin_password2_text)
        if not valid:
            flash(message, 'error')
            return redirect(url_for('admin_profile'))

        if valid and admin:
            if admin_contact_text:
                admin.userContact = admin_contact_text
            if admin_password1_text:
                hashed_pw = bcrypt.generate_password_hash(admin_password1_text).decode('utf-8')
                admin.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('admin_profile'))

    return render_template('admin/adminProfile.html', active_tab='admin_profiletab', admin_data=admin, admin_contact_text=admin_contact_text, 
                           admin_password1_text=admin_password1_text, admin_password2_text=admin_password2_text)























