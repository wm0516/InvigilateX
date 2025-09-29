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
from collections import defaultdict



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
@app.route('/get_courseCodeSection/<path:courseCodeSection_select>')
def get_courseCodeSection(courseCodeSection_select):
    course = Course.query.filter_by(courseCodeSection=courseCodeSection_select).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    return jsonify({
        "courseCodeSection": course.courseCodeSection,
        "courseDepartment": course.courseDepartment,
        "courseCode": course.courseCodeSection.split('/')[0] if '/' in course.courseCodeSection else course.courseCodeSection,
        "courseSection": course.courseCodeSection.split('/')[1] if '/' in course.courseCodeSection else "",
        "coursePractical": course.coursePractical,
        "courseTutorial": course.courseTutorial,
        "courseName": course.courseName,
        "courseHour": course.courseHour,
        "courseStudent": course.courseStudent,
        "courseStatus": course.courseStatus,
    })

# -------------------------------
# Function for Admin ManageCourse Route
# -------------------------------
@app.route('/admin/manageCourse', methods=['GET', 'POST'])
def admin_manageCourse():
    try:
        # === Load basic data safely ===
        course_data = Course.query.all() or []
        department_data = Department.query.all() or []

        course_id = request.form.get('editCourseSelect')
        course_select = Course.query.filter_by(courseCodeSection=course_id).first()

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

                if action == 'update' and course_select:
                    # Update course values
                    course_select.courseDepartment = request.form.get('departmentCode', '').strip()
                    course_select.courseName = request.form.get('courseName', '').strip()
                    course_select.coursePractical = request.form.get('practicalLecturerSelect', '').strip()
                    course_select.courseTutorial = request.form.get('tutorialLecturerSelect', '').strip()
                    course_select.courseStatus = True if request.form.get('editStatus') == '1' else False

                    # Safe int conversion
                    try:
                        course_select.courseHour = int(request.form.get('courseHour', 0))
                    except (ValueError, TypeError):
                        course_select.courseHour = 0

                    try:
                        course_select.courseStudent = int(request.form.get('courseStudent', 0))
                    except (ValueError, TypeError):
                        course_select.courseStudent = 0

                    # -------------------------
                    # Validate required fields
                    # -------------------------
                    required_fields = [
                        course_select.courseDepartment,
                        course_select.courseName,
                        course_select.coursePractical,
                        course_select.courseTutorial,
                        course_select.courseHour,
                        course_select.courseStudent
                    ]

                    if all(f is not None and f != '' for f in required_fields):
                        # Create Exam if none exists
                        if not course_select.courseExamId:
                            new_exam = Exam(
                                examVenue=None,
                                examStartTime=None,
                                examEndTime=None,
                                examNoInvigilator=None
                            )
                            db.session.add(new_exam)
                            db.session.flush()  # assign examId before commit
                            course_select.courseExamId = new_exam.examId

                    db.session.commit()
                    flash("Course updated successfully", "success")

                elif action == 'delete' and course_select:
                    course_select.courseStatus = False
                    db.session.commit()
                    flash("Course deleted successfully", "success")

                return redirect(url_for('admin_manageCourse'))

            # --- Manual Add Section ---
            elif form_type == 'manual':
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
            course_select=course_select,
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
# Get Department Details for ManageDepartmentEditPage
# -------------------------------
@app.route('/get_department/<path:department_code>')
def get_department(department_code):
    dept = Department.query.filter_by(departmentCode=department_code).first()
    if not dept:
        return jsonify({"error": "Department not found"}), 404
    return jsonify({
        "departmentCode": dept.departmentCode,
        "departmentName": dept.departmentName,
        "deanId": dept.deanId,
        "hopId": dept.hopId
    })

# -------------------------------
# Admin Manage Department
# -------------------------------
@app.route('/admin/manageDepartment', methods=['GET', 'POST'])
def admin_manageDepartment():
    # Load all departments and stats
    department_data = Department.query.all()
    total_department = len(department_data)
    total_dean = User.query.filter_by(userLevel=2).count()
    total_hop = User.query.filter_by(userLevel=3).count()

    # For edit section
    department_selected_code = request.form.get('editDepartment')
    department_select = Department.query.filter_by(departmentCode=department_selected_code).first()

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ---------------- Manual Section ----------------
        if form_type == 'manual':
            departmentCode = request.form.get('departmentCode')
            departmentName = request.form.get('departmentName')

            # Check if department code already exists
            if Department.query.filter_by(departmentCode=departmentCode).first():
                flash("Department code already exists. Please use a unique code.", "error")
            else:
                db.session.add(Department(departmentCode=departmentCode, departmentName=departmentName))
                db.session.commit()
                flash("New Department Added", "success")

        # ---------------- Edit Section ----------------
        elif form_type == 'edit' and department_select:
            action = request.form.get('action')
            departmentName = request.form.get('departmentName')
            deanId = request.form.get('deanName')
            hopId = request.form.get('hopName')

            # Validate Dean belongs to this department (only if a new selection is made)
            if deanId:
                dean_user = User.query.filter_by(userId=deanId, userLevel=2).first()
                if not dean_user or dean_user.userDepartment != department_select.departmentCode:
                    flash("Selected Dean/Hos does not belong to this department. Ignoring Dean/Hos selection.", "error")
                    deanId = None
            # Validate HOP belongs to this department (only if a new selection is made)
            if hopId:
                hop_user = User.query.filter_by(userId=hopId, userLevel=3).first()
                if not hop_user or hop_user.userDepartment != department_select.departmentCode:
                    flash("Selected Hop does not belong to this department. Ignoring Hop selection.", "error")
                    hopId = None

            if action == 'update':
                department_select.departmentName = departmentName
                # Update Dean only if a valid selection is made
                if deanId is not None:
                    department_select.deanId = deanId
                # Update HOP only if a valid selection is made
                if hopId is not None:
                    department_select.hopId = hopId
                db.session.commit()
                flash("Department updated successfully", "success")
            elif action == 'delete':
                db.session.delete(department_select)
                db.session.commit()
                flash("Department deleted successfully", "success")

            return redirect(url_for('admin_manageDepartment'))
    return render_template('admin/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data, department_select=department_select, total_department=total_department, total_dean=total_dean, total_hop=total_hop)



# -------------------------------
# Get Venue Details for ManageVenueEditPage
# -------------------------------
@app.route('/get_venue/<venue_number>')
def get_venue(venue_number):
    venue = Venue.query.filter_by(venueNumber=venue_number).first()
    if not venue:
        return jsonify({"error": "Venue not found"}), 404

    return jsonify({
        "venueNumber": venue.venueNumber,
        "venueLevel": venue.venueLevel,
        "venueCapacity": venue.venueCapacity
    })

# -------------------------------
# Function for Admin ManageVenue Route
# -------------------------------
@app.route('/admin/manageVenue', methods=['GET', 'POST'])
def admin_manageVenue():
    # Load all venues and stats
    venue_data = Venue.query.order_by(Venue.venueLevel.asc()).all()

    # Floor counts
    venues_by_floor = [
        {"floor": floor, "count": count}
        for floor, count in db.session.query(Venue.venueLevel, func.count())
        .group_by(Venue.venueLevel)
        .order_by(Venue.venueLevel)
        .all()
    ]

    # For edit section
    venue_selected_number = request.form.get('editVenueNumber')
    venue_select = Venue.query.filter_by(venueNumber=venue_selected_number).first()

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ---------------- Manual Section ----------------
        if form_type == 'manual':
            venueNumber = request.form.get('venueNumber', '').strip().upper()
            venueLevel = request.form.get('venueLevel', '').strip()
            venueCapacity = request.form.get('venueCapacity', '').strip()

            # Check if venue already exists
            if Venue.query.filter_by(venueNumber=venueNumber).first():
                flash("Venue Room Already Exists", "error")
            else:
                try: 
                    capacity = int(venueCapacity)
                    if capacity < 0:
                        raise ValueError
                    db.session.add(Venue(
                        venueNumber=venueNumber,
                        venueLevel=venueLevel,
                        venueCapacity=capacity
                    ))
                    db.session.commit()
                    flash("Venue Added", "success")
                except ValueError:
                    flash("Capacity must be a non-negative integer", "error")
            return redirect(url_for('admin_manageVenue'))

        # ---------------- Edit Section ----------------
        elif form_type == 'edit' and venue_select:
            action = request.form.get('action')
            venueLevel = request.form.get('venueLevel')
            venueCapacity = request.form.get('venueCapacity')

            if action == 'update':
                try:
                    capacity = int(venueCapacity)
                    if capacity < 0:
                        raise ValueError
                    venue_select.venueLevel = venueLevel
                    venue_select.venueCapacity = capacity
                    db.session.commit()
                    flash("Venue Updated", "success")
                except ValueError:
                    flash("Capacity must be a non-negative integer", "error")

            elif action == 'delete':
                try:
                    # Set related foreign keys to NULL
                    Exam.query.filter_by(examVenue=venue_select.venueNumber).update({"examVenue": None})
                    VenueAvailability.query.filter_by(venueNumber=venue_select.venueNumber).update({"venueNumber": None})
                    
                    db.session.commit()  # Commit the updates first
                    db.session.delete(venue_select)  # Delete the venue
                    db.session.commit()
                    flash("Venue Deleted, related references set to NULL", "success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"Failed to delete venue: {str(e)}", "error")
            return redirect(url_for('admin_manageVenue'))
    # Render template
    return render_template('admin/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data, venue_select=venue_select, venues_by_floor=venues_by_floor)





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
# Read All Course Under The Selected Department For ManageExamPage
# ------------------------------- 
@app.route('/get_courses_by_department/<department_code>')
def get_courses_by_department(department_code):
    courses = (
        db.session.query(Course)
        .join(Exam, Course.courseExamId == Exam.examId)
        .filter(
            Course.courseDepartment == department_code,
            Course.courseExamId.isnot(None),
            Exam.examStartTime.is_(None),
            Exam.examEndTime.is_(None),
            Exam.examVenue.is_(None),
            Exam.examNoInvigilator.is_(None)
        )
        .all()
    )

    courses_list = [
        {"courseCodeSection": c.courseCodeSection, "courseName": c.courseName}
        for c in courses
    ]
    return jsonify(courses_list)

# -------------------------------
# Read All CourseDetails Under Selected Department for ManageExamPage
# -------------------------------
@app.route('/get_course_details/<department_code>/<path:course_section>')
def get_course_details(department_code, course_section):
    course = Course.query.filter_by(
        courseDepartment=department_code,
        courseCodeSection=course_section
    ).first()

    if not course:
        return jsonify({"error": "Course not found"}), 404

    return jsonify({
        "courseCodeSection": course.courseCodeSection,
        "courseName": course.courseName,
        "practicalLecturer": course.coursePractical,
        "tutorialLecturer": course.courseTutorial,
        "courseStudent": course.courseStudent
    })

# -------------------------------
# Get ExamDetails for ManageExamEditPage
# -------------------------------
@app.route('/get_exam_details/<path:course_code_section>')
def get_exam_details(course_code_section):
    course = Course.query.filter_by(courseCodeSection=course_code_section).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    exam = Exam.query.filter_by(examId=course.courseExamId).first() if course.courseExamId else None

    response_data = {
        "courseCodeSection": course.courseCodeSection,
        "courseName": course.courseName or "",
        "courseDepartment": course.courseDepartment or "",
        "practicalLecturer": course.practicalLecturer.userName if course.practicalLecturer else "",
        "tutorialLecturer": course.tutorialLecturer.userName if course.tutorialLecturer else "",
        "courseStudent": course.courseStudent or 0,
        "examStartTime": exam.examStartTime.strftime("%Y-%m-%dT%H:%M") if exam and exam.examStartTime else "",
        "examEndTime": exam.examEndTime.strftime("%Y-%m-%dT%H:%M") if exam and exam.examEndTime else "",
        "examVenue": exam.examVenue if exam else "",
        "examNoInvigilator": exam.examNoInvigilator if exam else 0
    }
    return jsonify(response_data)

# -------------------------------
# Get VenueDetails for ManageExamEditPage
# -------------------------------
@app.route('/get_available_venues')
def get_available_venues():
    try:
        student_count = int(request.args.get('students', 0))
        start_dt_str = request.args.get('start')
        end_dt_str = request.args.get('end')

        if not start_dt_str or not end_dt_str:
            return jsonify([])

        start_dt = datetime.strptime(start_dt_str, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_dt_str, "%Y-%m-%dT%H:%M")

        # Query venues with enough capacity
        venues = Venue.query.filter(Venue.venueCapacity >= student_count).all()

        available_venues = []

        for v in venues:
            # Check if venue has overlapping exam in VenueAvailability
            overlap = VenueAvailability.query.filter(
                VenueAvailability.venueNumber == v.venueNumber,
                VenueAvailability.startDateTime < end_dt,
                VenueAvailability.endDateTime > start_dt
            ).first()

            if not overlap:
                available_venues.append({
                    "venueNumber": v.venueNumber,
                    "venueCapacity": v.venueCapacity
                })

        return jsonify(available_venues)
    
    except Exception as e:
        print(f"[Error fetching available venues] {e}")
        return jsonify([])


def adjust_invigilators(report, new_count, start_dt, end_dt):
    pending_hours = (end_dt - start_dt).total_seconds() / 3600.0

    current_attendances = list(report.attendances)
    current_count = len(current_attendances)

    if new_count == current_count:
        return  # nothing to change

    if new_count > current_count:
        # Need to ADD more invigilators
        extra_needed = new_count - current_count
        already_assigned_ids = [att.invigilatorId for att in current_attendances]

        eligible_invigilators = User.query.filter(
            User.userLevel == 1,
            ~User.userId.in_(already_assigned_ids)
        ).all()

        if not eligible_invigilators:
            raise ValueError("No extra eligible invigilators available")

        random.shuffle(eligible_invigilators)
        for inv in eligible_invigilators[:extra_needed]:
            inv.userPendingCumulativeHours = (inv.userPendingCumulativeHours or 0) + pending_hours
            db.session.add(InvigilatorAttendance(
                reportId=report.invigilationReportId,
                invigilatorId=inv.userId
            ))

    else:  
        # Need to REMOVE invigilators
        remove_count = current_count - new_count
        to_remove = random.sample(current_attendances, remove_count)
        for att in to_remove:
            inv = att.invigilator
            if inv:
                inv.userPendingCumulativeHours = max(
                    0.0,
                    (inv.userPendingCumulativeHours or 0.0) - pending_hours
                )
            db.session.delete(att)

    db.session.commit()



# -------------------------------
# Function for Admin ManageExam Route
# -------------------------------
@app.route('/admin/manageExam', methods=['GET', 'POST'])
def admin_manageExam():
    department_data = Department.query.all()
    venue_data = Venue.query.all()

    # Base query: only exams whose course is active
    exam_data_query = Exam.query.join(Exam.course).filter(Course.courseStatus == True)

    # Fetch all exam_data as list
    exam_data_list = exam_data_query.all()
    total_exam = len(exam_data_list)

    # For Edit section
    exam_selected = request.form.get('editExamCourseSection')
    course = Course.query.filter_by(courseCodeSection=exam_selected).first()
    exam_select = Exam.query.filter_by(examId=course.courseExamId).first() if course else None

    unassigned_exam = len([
        e for e in exam_data_list
        if e.examStartTime is None
        and e.examEndTime is None
        and e.examVenue is None
        and (e.examNoInvigilator is None or e.examNoInvigilator == 0)
    ])

    complete_exam = len([
        e for e in exam_data_list
        if e.examStartTime is not None
        and e.examEndTime is not None
        and e.examVenue is not None
        and e.examNoInvigilator not in (None, 0)
    ])

    incomplete_exam = len(exam_data_list) - unassigned_exam - complete_exam

    # Default manual form values
    courseSection_text = practicalLecturer_text = tutorialLecturer_text = venue_text = invigilatorNo_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # --------------------- UPLOAD ADD EXAM FORM ---------------------
        if form_type == 'upload':
            return handle_file_upload(
                file_key='exam_file',
                expected_cols=['date', 'day', 'start', 'end', 'program','course/sec','lecturer','no of','room'],
                process_row_fn=process_exam_row,
                redirect_endpoint='admin_manageExam',
                usecols="A:I"
            )

        # --------------------- EDIT EXAM FORM ---------------------
        elif form_type == 'edit' and exam_select:
            action = request.form.get('action')
            start_dt_raw = request.form.get('startDateTime', '').strip()
            end_dt_raw = request.form.get('endDateTime', '').strip()

            if not start_dt_raw or not end_dt_raw:
                flash("Start or end date/time is missing", "error")
                return redirect(url_for('admin_manageExam'))

            start_dt = datetime.strptime(start_dt_raw, "%Y-%m-%dT%H:%M")
            end_dt = datetime.strptime(end_dt_raw, "%Y-%m-%dT%H:%M")

            venue_text = request.form.get('venue', '').strip()
            invigilatorNo_text = request.form.get('invigilatorNo', '0').strip()

            if action == 'update':
                venue_obj = Venue.query.filter_by(venueNumber=venue_text).first()

                if not venue_obj:
                    flash(f"Selected venue {venue_text} does not exist", "error")
                elif venue_obj.venueCapacity < exam_select.course.courseStudent:
                    flash(f"Venue capacity ({venue_obj.venueCapacity}) cannot fit {exam_select.course.courseStudent} student(s)", "error")
                else:
                    # Update exam fields
                    exam_select.examStartTime = start_dt
                    exam_select.examEndTime = end_dt
                    exam_select.examVenue = venue_text
                    exam_select.examNoInvigilator = invigilatorNo_text

                    # Manage related InvigilationReport + Attendances
                    existing_report = InvigilationReport.query.filter_by(examId=exam_select.examId).first()

                    if not existing_report:
                        # No report exists → create new
                        create_exam_and_related(
                            start_dt, end_dt,
                            exam_select.course.courseCodeSection,
                            venue_text,
                            exam_select.course.coursePractical,
                            exam_select.course.courseTutorial,
                            invigilatorNo_text
                        )
                    elif exam_select.examNoInvigilator != int(invigilatorNo_text):
                        report = InvigilationReport.query.filter_by(examId=exam_select.examId).first()
                        if report:
                            adjust_invigilators(report, int(invigilatorNo_text), start_dt, end_dt)
                        else:
                            create_exam_and_related(start_dt, end_dt,exam_select.course.courseCodeSection,venue_text,exam_select.course.coursePractical,exam_select.course.courseTutorial,invigilatorNo_text)

                    db.session.commit()
                    flash("Exam updated successfully", "success")

            elif action == 'delete':
                # Delete all related reports (cascade removes attendances too)
                reports = InvigilationReport.query.filter_by(examId=exam_select.examId).all()
                for report in reports:
                    db.session.delete(report)

                db.session.delete(exam_select)
                db.session.commit()
                flash("Exam deleted successfully", "success")

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

                flash(message, "success" if success else "error")
                return redirect(url_for('admin_manageExam'))

            except Exception as manual_err:
                print(f"[Manual Form Error] {manual_err}")
                traceback.print_exc()
                flash(f"Error processing manual form: {manual_err}", "error")
                return redirect(url_for('admin_manageExam'))

    return render_template(
        'admin/adminManageExam.html',
        active_tab='admin_manageExamtab',
        exam_data=exam_data_list,
        unassigned_exam=unassigned_exam,
        venue_data=venue_data,
        department_data=department_data,
        total_exam=total_exam,
        complete_exam=complete_exam,
        incomplete_exam=incomplete_exam,
        exam_select=exam_select
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
# Read All StaffDetails Under The ManageLecturerEditPage
# -------------------------------
@app.route('/get_staff/<id>')
def get_staff(id):
    user = User.query.filter_by(userId=id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "userId": user.userId,
        "userName": user.userName,
        "userEmail": user.userEmail,
        "userContact": user.userContact,
        "userGender": user.userGender,
        "userLevel": str(user.userLevel),
        "userDepartment": user.userDepartment or "",
        "userStatus": str(user.userStatus)
    })

# -------------------------------
# Function for Admin ManageStaff Route
# -------------------------------
@app.route('/admin/manageStaff', methods=['GET', 'POST'])
def admin_manageStaff():
    user_data = User.query.all()
    department_data = Department.query.all()

    # === Dashboard Counts ===
    total_staff = User.query.count()
    total_admin = User.query.filter_by(userLevel=4).count()
    total_lecturer = User.query.filter_by(userLevel=1).count()
    total_dean = User.query.filter_by(userLevel=2).count()
    total_hop = User.query.filter_by(userLevel=3).count()
    total_male_staff = User.query.filter_by(userGender="MALE").count()
    total_female_staff = User.query.filter_by(userGender="FEMALE").count()
    total_activated = User.query.filter_by(userStatus=1).count()
    total_deactivate = User.query.filter_by(userStatus=0).count()
    total_deleted = User.query.filter_by(userStatus=2).count()

    # Incomplete rows check
    error_rows = User.query.filter(
        (User.userDepartment.is_(None)) | (User.userDepartment == '') |
        (User.userName.is_(None)) | (User.userName == '') |
        (User.userEmail.is_(None)) | (User.userEmail == '') |
        (User.userContact.is_(None)) | (User.userContact == '') |
        (User.userGender.is_(None)) | (User.userGender == '') |
        (User.userLevel.is_(None))
    ).count()

    staff_id = request.form.get('editStaffId')
    user_select = User.query.filter_by(userId=staff_id).first()

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

        elif form_type == 'edit':
            action = request.form.get('action')
            if action == 'update' and user_select:
                user_select.userName = request.form['editUsername']
                user_select.userEmail = request.form['editEmail']
                user_select.userContact = request.form['editContact']
                user_select.userGender = request.form['editGender']
                user_select.userLevel = int(request.form['editRole'])
                user_select.userDepartment = request.form['editDepartment']
                user_select.userStatus = int(request.form['editStatus']) 

                # In case user delete by updated    
                if user_select.userStatus == 2:
                    user_select.userRegisterDateTime = datetime.now(timezone.utc)

                db.session.commit()
                flash("Staff updated successfully", "success")

            elif action == 'delete' and user_select:
                user_select.userStatus = 2
                user_select.userRegisterDateTime = datetime.now(timezone.utc)
                db.session.commit() 
                flash("Staff deleted successfully", "success")

            return redirect(url_for('admin_manageStaff'))

        elif form_type == 'manual':
            role_text = request.form.get('role', '0')
            form_data = {
                "id": request.form.get('userid', '').strip(),
                "department": request.form.get('department', '').strip(),
                "name": request.form.get('username', '').strip(),
                "role": int(role_text),
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
        total_dean=total_dean,
        total_lecturer=total_lecturer,
        total_male_staff=total_male_staff,
        total_female_staff=total_female_staff,
        total_activated=total_activated,
        total_deactivate=total_deactivate,
        total_deleted=total_deleted,
        error_rows=error_rows,
        user_select=user_select
    )






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
# Extract time from the database
# -------------------------------
def parse_date_range(date_range):
    """Parse classWeekDate 'MM/DD/YYYY-MM/DD/YYYY' and return (start, end) datetime."""
    if not date_range:
        return None, None
    try:
        start_str, end_str = date_range.split("-")
        start = datetime.strptime(start_str.strip(), "%m/%d/%Y")
        end = datetime.strptime(end_str.strip(), "%m/%d/%Y")
        return start, end
    except Exception:
        return None, None

# -------------------------------
# Get TimetableLink Details for ManageTimetableEditPage
# -------------------------------
@app.route('/get_linkTimetable/<path:timetableID>')
def get_linkTimetable(timetableID):
    timetable = Timetable.query.filter_by(timetableId=timetableID).first()
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404
    return jsonify({
        "timetableId": timetable.timetableId,
        "user_id": timetable.user_id
    })

# -------------------------------
# Save Parsed Timetable to DB
# -------------------------------
def save_timetable_to_db(structured):
    lecturer = structured.get("lecturer")
    filename = structured.get("filename")

    if not lecturer:
        return 0

    user = User.query.filter_by(userName=lecturer).first()

    if user:
        timetable = Timetable.query.filter_by(user_id=user.userId).first()
        if timetable:
            TimetableRow.query.filter_by(timetable_id=timetable.timetableId).delete()
        else:
            timetable = Timetable(user_id=user.userId)
            db.session.add(timetable)
            db.session.commit()
    else:
        timetable = None

    new_rows = []
    rows_inserted = 0   # <--- track how many inserted

    for day, activities in structured["days"].items():
        for act in activities:
            if not (act.get("class_type") and act.get("time") and act.get("room") and act.get("course")):
                continue
            if act.get("sections"):
                for sec in act["sections"]:
                    if not (sec.get("intake") and sec.get("course_code") and sec.get("section")):
                        continue

                    new_entry = {
                        "timetable_id"  : timetable.timetableId if timetable else None,
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
                    }

                    existing = TimetableRow.query.filter_by(
                        lecturerName=lecturer,
                        classType=new_entry["classType"],
                        classDay=new_entry["classDay"],
                        classTime=new_entry["classTime"],
                        classRoom=new_entry["classRoom"],
                        courseName=new_entry["courseName"],
                        courseIntake=new_entry["courseIntake"],
                        courseCode=new_entry["courseCode"],
                        courseSection=new_entry["courseSection"],
                    ).first()

                    if existing and existing.classWeekDate and new_entry["classWeekDate"]:
                        old_start, _ = parse_date_range(existing.classWeekDate)
                        new_start, _ = parse_date_range(new_entry["classWeekDate"])

                        if old_start and new_start:
                            if new_start > old_start:
                                db.session.delete(existing)
                                db.session.add(TimetableRow(**new_entry))
                                rows_inserted += 1
                            elif new_start < old_start:
                                continue
                            else:
                                continue
                        else:
                            db.session.delete(existing)
                            db.session.add(TimetableRow(**new_entry))
                            rows_inserted += 1
                    else:
                        db.session.add(TimetableRow(**new_entry))
                        rows_inserted += 1

    db.session.commit()
    return rows_inserted   # <--- return actual count


# -------------------------------
# Function for Admin ManageTimetable Route
# -------------------------------
@app.route('/admin/manageTimetable', methods=['GET', 'POST'])
def admin_manageTimetable():
    # ---- Default GET rendering ----
    timetable_data = TimetableRow.query.order_by(TimetableRow.rowId.asc()).all()
    lecturers = sorted({row.lecturerName for row in timetable_data})
    selected_lecturer = request.args.get("lecturer")

    # Use Timetable directly (not TimetableRow)
    total_timetable = db.session.query(func.count(func.distinct(TimetableRow.lecturerName))).scalar()
    timetable_list = Timetable.query.filter(Timetable.timetableId != None).all()

    # Predefine timetable_select to avoid UnboundLocalError
    timetable_select = None
    timetable_selected = request.form.get('editTimetableList')
    if timetable_selected:
        timetable_select = Timetable.query.filter_by(timetableId=timetable_selected).first()

    # Staff list (exclude certain levels/status)
    staff_list = User.query.filter(
        User.userLevel != 4,
        User.userStatus != 2
    ).all()

    # Count timetable per day
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    day_counts = {
        f"{day.lower()}_timetable": db.session.query(TimetableRow.courseCode)
            .filter(TimetableRow.classDay == day).distinct().count()
        for day in days
    }

    # Group all lecturers with unassigned rows
    grouped_unassigned = defaultdict(int)
    for row in TimetableRow.query.filter_by(timetable_id=None).all():
        grouped_unassigned[row.lecturerName] += 1

    unassigned_summary = [{"lecturer": name, "count": count} for name, count in grouped_unassigned.items()]

    # Build mapping: user_id -> timetableId
    timetable_map = {t.user_id: t.timetableId for t in timetable_list}

    # ---- POST Handling ----
    if request.method == "POST":
        form_type = request.form.get('form_type')

        if form_type == 'upload':
            # ---- File Upload Handling ----
            files = request.files.getlist("timetable_file[]")
            latest_files = {}
            skipped_files = []

            # Filter to keep only the latest timestamp for each base_name
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

            # Process each latest file
            total_rows_inserted = 0
            total_files_processed = 0
            for base_name, (timestamp, file) in latest_files.items():
                reader = PyPDF2.PdfReader(file.stream)
                raw_text = "".join(page.extract_text() + " " for page in reader.pages if page.extract_text())
                structured = parse_timetable(raw_text)
                structured['filename'] = file.filename
                rows_inserted = save_timetable_to_db(structured)

                total_rows_inserted += rows_inserted
                if rows_inserted > 0:
                    total_files_processed += 1   # count only if rows were actually inserted

            flash(f"Files read: {len(files)}, Files processed: {total_files_processed}, Rows inserted: {total_rows_inserted}, Files skipped: {len(skipped_files)}", "success")
            return redirect(url_for('admin_manageTimetable'))
        
        elif form_type == 'manual':
            user_id = request.form.get("staffList")      # <-- this is User.userId
            lecturer = request.form.get("lecturerName")

            if user_id and lecturer:
                # Ensure this user has a Timetable entry
                timetable = Timetable.query.filter_by(user_id=user_id).first()
                if not timetable:
                    timetable = Timetable(user_id=user_id)
                    db.session.add(timetable)
                    db.session.commit()  # commit so timetableId is generated

                # Now update all rows for that lecturer
                rows = TimetableRow.query.filter_by(lecturerName=lecturer, timetable_id=None).all()
                for row in rows:
                    row.timetable_id = timetable.timetableId   # <-- valid FK

                db.session.commit()
                flash(f"{lecturer} Timetable  linked to staff ID {user_id}", "success")
            else:
                flash("Missing lecturer or staff", "error")

            return redirect(url_for('admin_manageTimetable'))
        
        elif form_type == 'edit':
            action = request.form.get('action')
            if action == 'update' and timetable_select:
                new_user_id = request.form['editStaffList']

                # Case 1: Same staff already linked → success
                if str(timetable_select.user_id) == new_user_id:
                    flash("No changes made. Timetable already linked to this staff.", "success")

                else:
                    # Check if this staff is already linked to another timetable
                    existing = Timetable.query.filter(
                        Timetable.user_id == new_user_id,
                        Timetable.timetableId != timetable_select.timetableId
                    ).first()

                    if existing:
                        # Case 2: Found in another timetable → error
                        flash(f"Staff ID:{new_user_id} is already linked to another timetable(ID:{existing.timetableId}).", "error")
                    else:
                        # Case 3: Not found → update
                        timetable_select.user_id = new_user_id
                        db.session.commit()
                        flash("Timetable updated successfully.", "success")

            elif action == 'delete' and timetable_select:
                db.session.delete(timetable_select)
                db.session.commit()
                flash("Timetable deleted successfully.", "success")

                return redirect(url_for('admin_manageTimetable'))

    return render_template('admin/adminManageTimetable.html',active_tab='admin_manageTimetabletab',timetable_data=timetable_data,lecturers=lecturers,selected_lecturer=selected_lecturer,total_timetable=total_timetable,
        unassigned_summary=unassigned_summary,staff_list=staff_list,**day_counts,timetable_list=timetable_list,timetable_map=timetable_map,timetable_select=timetable_select)





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
    # Use LEFT OUTER JOIN to keep all InvigilatorAttendance rows
    query = db.session.query(
        InvigilatorAttendance.attendanceId,
        InvigilatorAttendance.invigilatorId,    
        InvigilatorAttendance.checkIn,
        InvigilatorAttendance.checkOut,
        Exam.examStartTime,
        Exam.examEndTime,
        InvigilatorAttendance.reportId
    ).outerjoin(Exam, Exam.examId == InvigilatorAttendance.reportId).all()

    # Total reports and total assigned invigilators
    total_report = InvigilationReport.query.count()
    total_invigilator = InvigilatorAttendance.query.count()

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

        # Case 3: Both checkIn and checkOut exist
        # If Exam times are missing, skip time comparison
        if row.examStartTime is not None:
            if row.checkIn <= row.examStartTime:
                stats["total_checkInOnTime"] += 1
            else:
                stats["total_checkInLate"] += 1

        if row.examEndTime is not None:
            if row.checkOut >= row.examEndTime:
                stats["total_checkOutOnTime"] += 1
            else:
                stats["total_checkOutEarly"] += 1

    return stats

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


