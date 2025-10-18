import os
import re
import warnings
from io import BytesIO
from collections import defaultdict
from datetime import datetime
import random
import pandas as pd
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import NamedStyle
import PyPDF2
from flask import render_template, request, redirect, url_for,flash, session, jsonify, send_file
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import func, and_, or_, case
from app import app
from .authRoutes import login_required
from .backend import *
from .database import *

# Initialize serializer and bcrypt
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

# Upload configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



# -------------------------------
# Function handle file upload
# -------------------------------
def handle_file_upload(file_key, expected_cols, process_row_fn, redirect_endpoint, usecols="A:Z", skiprows=1):
    file = request.files.get(file_key)
    if file and file.filename:
        try:
            file_stream = BytesIO(file.read())
            excel_file = pd.ExcelFile(file_stream)
            records_added = records_failed = 0

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols=usecols,
                        skiprows=skiprows,      # skip the first row(s)
                        header=0,               # take the next row as header
                        dtype=str
                    )
                    df.columns = [str(col).strip().lower() for col in df.columns]

                    if not set(expected_cols).issubset(df.columns):
                        flash(f"{df.columns}","error")
                        raise ValueError(f"Excel columns do not match expected format: {df.columns.tolist()}")

                    # normalize all columns
                    for col in df.columns:
                        df[col] = df[col].apply(lambda x: str(x).strip() if isinstance(x, str) else x)

                    # process each row using the provided callback
                    for _, row in df.iterrows():
                        try:
                            success, message = process_row_fn(row)
                            if success:
                                records_added += 1
                            else:
                                records_failed += 1
                                flash(f"Row failed: {message}", "error")
                        except Exception as row_err:
                            records_failed += 1
                            flash(f"Row processing error: {str(row_err)} | Data: {row.to_dict()}", "error")

                except Exception as sheet_err:
                    pass
            if records_added > 0:
                flash(f"Successfully uploaded {records_added} record(s)", "success")
            if records_failed > 0:
                flash(f"Failed to upload {records_failed} record(s)", "error")
            if records_added == 0 and records_failed == 0:
                flash("No data uploaded", "error")

            return redirect(url_for(redirect_endpoint))
        except Exception as e:
            flash("File processing error: File upload in wrong format", "error")
            return redirect(url_for(redirect_endpoint))
    else:
        flash("No file uploaded", "error")
        return redirect(url_for(redirect_endpoint))

# -------------------------------
# Function for Admin ManageCourse Download Excel File Format 
# -------------------------------
def generate_managecourse_template(department_code=None):
    warnings.simplefilter("ignore", UserWarning)
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None, "Workbook has no active worksheet"
    ws.title = "Courses"
    
    # Header row (start from row 2)
    ws.append([])
    headers = ['Department Code', 'Course Code', 'Course Section', 'Course Name', 'Credit Hour', 'Practical Lecturer', 'Tutorial Lecturer', 'No of Students']
    ws.append(headers)
    
    # Hidden sheet for dropdown lists
    ws_lists = wb.create_sheet(title="Lists")

    # Departments
    if department_code:  
        departments = [department_code]   # single department
    else:  
        departments = [d.departmentCode for d in Department.query.all()]  # fallback: all

    for i, dept in enumerate(departments, start=1):
        ws_lists[f"A{i}"] = dept

    # Lecturers (filtered by department if needed)
    lecturers_query = User.query.filter_by(userLevel=1)
    if department_code:
        lecturers_query = lecturers_query.filter_by(userDepartment=department_code)

    lecturers = [u.userId for u in lecturers_query.all()]
    for i, lec in enumerate(lecturers, start=1):
        ws_lists[f"B{i}"] = lec

    ws_lists.sheet_state = 'hidden'
    
    # Dropdowns
    if departments:
        dv_dept = DataValidation(type="list", formula1=f"=Lists!$A$1:$A${len(departments)}", allow_blank=False)
        ws.add_data_validation(dv_dept)
        dv_dept.add("A3:A1000")
    
    if lecturers:
        dv_lecturer = DataValidation(type="list", formula1=f"=Lists!$B$1:$B${len(lecturers)}", allow_blank=True)
        ws.add_data_validation(dv_lecturer)
        dv_lecturer.add("F3:F1000")
        dv_lecturer.add("G3:G1000")
    
    # Return BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# -------------------------------
# Function for Admin ManageCourse Download Excel File Template
# -------------------------------
@app.route('/download_course_template/<department_code>')
@login_required
def download_course_template(department_code):
    output = generate_managecourse_template(department_code)
    return send_file(
        output,
        as_attachment=True, 
        download_name=f"ManageCourse_{department_code}.xlsx", # type: ignore[arg-type]
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------------
# Function for Admin ManageCourse Route Upload File
# -------------------------------
def process_course_row(row):
    return create_course_and_exam(
        department  = str(row['department code']).strip(),
        code        = str(row['course code']).strip().replace(" ", ""),
        section     = str(row['course section']).strip().replace(" ", ""),
        name        = str(row['course name']).strip(),
        hour        = int(row['credit hour']),
        practical   = str(row['practical lecturer']).strip().upper(),
        tutorial    = str(row['tutorial lecturer']).strip().upper(),
        students    = int(row['no of students']),
    )

# -------------------------------
# Read All LecturerName Under The Selected Department For ManageCoursePage
# -------------------------------
@app.route('/get_lecturers_by_department/<department_code>')
@login_required
def get_lecturers_by_department(department_code):
    # Ensure case-insensitive match if needed
    lecturers = User.query.filter_by(userDepartment=department_code, userLevel=1).all()
    lecturers_list = [{"userId": l.userId, "userName": l.userName} for l in lecturers]
    return jsonify(lecturers_list) 

# -------------------------------
# Read All CourseCodeSection and Return all the selected data details Under The ManageCourseEditPage
# -------------------------------
@app.route('/get_courseCodeSection/<path:courseCodeSection_select>')
@login_required
def get_courseCodeSection(courseCodeSection_select):
    course = Course.query.filter_by(courseCodeSectionIntake=courseCodeSection_select).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    return jsonify({
        "courseCodeSection" : course.courseCodeSectionIntake,
        "courseDepartment"  : course.courseDepartment,
        "coursePractical"   : course.coursePractical,
        "courseTutorial"    : course.courseTutorial,
        "courseName"        : course.courseName,
        "courseHour"        : course.courseHour,
        "courseStudent"     : course.courseStudent,
        "courseStatus"      : course.courseStatus,
    })

# -------------------------------
# Function for Admin ManageCourse Route
# -------------------------------
@app.route('/admin/manageCourse', methods=['GET', 'POST'])
@login_required
def admin_manageCourse():
    course_data = Course.query.order_by(
        Course.coursePractical.asc(),
        Course.courseTutorial.asc(),
        Course.courseStatus.desc(),
        Course.courseDepartment.asc()
    ).all()
    department_data = Department.query.all()

    course_id = request.form.get('editCourseSelect')
    course_select = Course.query.filter_by(courseCodeSectionIntake=course_id).first()

    # Count rows with missing/empty values
    error_rows = Course.query.filter(
        (Course.courseDepartment.is_(None)) | (Course.courseDepartment == '') |
        (Course.courseCodeSectionIntake.is_(None)) | (Course.courseCodeSectionIntake == '') |
        (Course.courseName.is_(None)) | (Course.courseName == '') |
        (Course.courseHour.is_(None)) |
        (Course.courseStudent.is_(None)) |
        (Course.coursePractical.is_(None)) | (Course.coursePractical == '') |
        (Course.courseTutorial.is_(None)) | (Course.courseTutorial == '')
    ).count()

    # === Courses by department safely ===
    courses_by_department_raw = (
        db.session.query(
            func.coalesce(Department.departmentCode, "Unknown").label("department"),
            func.count(Course.courseCodeSectionIntake).label("course_count")
        )
        .outerjoin(Course, Department.departmentCode == Course.courseDepartment)
        .filter(Course.courseStatus == True)   # ✅ filter BEFORE group_by
        .group_by(func.coalesce(Department.departmentCode, "Unknown"))
        .having(func.count(Course.courseCodeSectionIntake) > 0)
        .order_by(func.coalesce(Department.departmentCode, "Unknown").asc())
        .all()
        or []
    )

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
                usecols="A:H",
                skiprows=1 
            )

        # --- Edit Section ---
        elif form_type == 'edit':
            action = request.form.get('action')
            if action == 'update' and course_select:
                # Update course values
                course_select.courseDepartment  = request.form.get('departmentCode', '').strip()
                course_select.courseName        = request.form.get('courseName', '').strip()
                course_select.coursePractical   = request.form.get('practicalLecturerSelect', '').strip()
                course_select.courseTutorial    = request.form.get('tutorialLecturerSelect', '').strip()
                course_select.courseStatus      = True if request.form.get('courseStatus') == '1' else False

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

                invigilatorNo = 3 if course_select.courseStudent > 32 else 2

                if all(f is not None and f != '' for f in required_fields):
                    # Update existing exam if it already exists
                    if course_select.courseExamId:
                        existing_exam = Exam.query.get(course_select.courseExamId)
                        if existing_exam:
                            existing_exam.examNoInvigilator = invigilatorNo
                    else:
                        # Create new exam if none exists
                        new_exam = Exam(
                            examStartTime=None,
                            examEndTime=None,
                            examNoInvigilator=invigilatorNo
                        )
                        db.session.add(new_exam)
                        db.session.flush()
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
                "code"      : request.form.get('courseCode', '').replace(' ', ''),
                "section"   : request.form.get('courseSection', '').replace(' ', ''),
                "name"      : request.form.get('courseName', '').strip(),
                "hour"      : safe_int(request.form.get('courseHour')),
                "practical" : request.form.get('practicalLecturerSelect', '').strip(),
                "tutorial"  : request.form.get('tutorialLecturerSelect', '').strip(),
                "students"  : safe_int(request.form.get('courseStudent')),
            }
            success, message = create_course_and_exam(**form_data)
            flash(message, "success" if success else "error")
            return redirect(url_for('admin_manageCourse'))

    # === GET Request ===
    return render_template('admin/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, course_select=course_select,
                            department_data=department_data, courses_by_department=courses_by_department, error_rows=error_rows)





# -------------------------------
# Get Department Details for ManageDepartmentEditPage
# -------------------------------
@app.route('/get_department/<path:department_code>')
@login_required
def get_department(department_code):
    dept = Department.query.filter_by(departmentCode=department_code).first()
    if not dept:
        return jsonify({"error": "Department not found"}), 404
    return jsonify({
        "departmentCode": dept.departmentCode,
        "departmentName": dept.departmentName,
        "deanId"        : dept.deanId,
        "hosId"         : dept.hosId,
        "hopId"         : dept.hopId
    })

# -------------------------------
# Admin Manage Department
# -------------------------------
@app.route('/admin/manageDepartment', methods=['GET', 'POST'])
@login_required
def admin_manageDepartment():
    # Load all departments and stats
    department_data     = Department.query.all()
    total_department    = len(department_data)
    deans               = User.query.filter_by(userLevel=2).all()
    hoss                = User.query.filter_by(userLevel=3).all()
    hops                = User.query.filter_by(userLevel=4).all()

    # For edit section
    department_selected_code = request.form.get('editDepartment')
    department_select        = Department.query.filter_by(departmentCode=department_selected_code).first()

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
            action           = request.form.get('action')
            departmentName   = request.form.get('departmentName')
            hosId            = request.form.get('hosName')
            deanId           = request.form.get('deanName')
            hopId            = request.form.get('hopName')

            # Validate Dean belongs to this department (only if a new selection is made)
            if deanId:
                dean_user = User.query.filter_by(userId=deanId, userLevel=2).first()
                if not dean_user or dean_user.userDepartment != department_select.departmentCode:
                    flash("Selected Dean does not belong to this department. Ignoring Dean selection.", "error")
                    deanId = None
            # Validate Hos belongs to this department (only if a new selection is made)
            if hosId:
                hos_user = User.query.filter_by(userId=hosId, userLevel=3).first()
                if not hos_user or hos_user.userDepartment != department_select.departmentCode:
                    flash("Selected Hos does not belong to this department. Ignoring Hos selection.", "error")
                    hosId = None
            # Validate HOP belongs to this department (only if a new selection is made)
            if hopId:
                hop_user = User.query.filter_by(userId=hopId, userLevel=4).first()
                if not hop_user or hop_user.userDepartment != department_select.departmentCode:
                    flash("Selected Hop does not belong to this department. Ignoring Hop selection.", "error")
                    hopId = None

            if action == 'update':
                department_select.departmentName = departmentName
                # Update Dean only if a valid selection is made
                if deanId is not None:
                    department_select.deanId = deanId
                # Update Hos only if a valid selection is made
                if hosId is not None:
                    department_select.hosId = hosId
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
    return render_template('admin/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data, department_select=department_select, total_department=total_department, deans=deans, hoss=hoss, hops=hops)




# -------------------------------
# Get Venue Details for ManageVenueEditPage
# -------------------------------
@app.route('/get_venue/<venue_number>')
@login_required
def get_venue(venue_number):
    venue = Venue.query.filter_by(venueNumber=venue_number).first()
    if not venue:
        return jsonify({"error": "Venue not found"}), 404

    return jsonify({
        "venueNumber"   : venue.venueNumber,
        "venueLevel"    : venue.venueLevel,
        "venueCapacity" : venue.venueCapacity
    })

# -------------------------------
# Function for Admin ManageVenue Route
# -------------------------------
@app.route('/admin/manageVenue', methods=['GET', 'POST'])
@login_required
def admin_manageVenue():
    # Load all venues and stats
    venue_data = Venue.query.order_by(Venue.venueLevel.asc()).all()

    # For edit section
    venue_selected_number   = request.form.get('editVenueNumber')
    venue_select            = Venue.query.filter_by(venueNumber=venue_selected_number).first()

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ---------------- Manual Section ----------------
        if form_type == 'manual':
            venueNumber     = request.form.get('venueNumber', '').strip().upper()
            venueLevel      = request.form.get('venueLevel', '').strip()
            venueCapacity   = request.form.get('venueCapacity', '').strip()

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
            action          = request.form.get('action')
            venueLevel      = request.form.get('venueLevel')
            venueCapacity   = request.form.get('venueCapacity')

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
                    VenueExam.query.filter_by(venueNumber=venue_select.venueNumber).update({"venueNumber": None})
                    db.session.commit()  # Commit the updates first

                    db.session.delete(venue_select)  # Delete the venue
                    db.session.commit()
                    flash("Venue Deleted, related references set to NULL", "success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"Failed to delete venue: {str(e)}", "error")
            return redirect(url_for('admin_manageVenue'))
    # Render template
    return render_template('admin/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data, venue_select=venue_select)





# -------------------------------
# Function for Admin ManageExam Download Excel File Format
# -------------------------------
def generate_manageexam_template():
    warnings.simplefilter("ignore", UserWarning)
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None, "Workbook has no active worksheet"
    ws.title = "Exams"

    # First row empty
    ws.append([])
    # Second row = headers
    headers = ['Date', 'Day', 'Start', 'End', 'Program', 'Course/Sec', 'Lecturer', 'No of', 'Room']
    ws.append(headers)

    # === Apply formatting ===
    date_style = NamedStyle(name="date_style", number_format="MM/DD/YYYY")

    for row in range(3, 503):
        # Column A = Date with date format
        ws[f"A{row}"].style = date_style
        # Column B = Day (auto formula from date)
        ws[f"B{row}"] = f'=IF(A{row}="","",TEXT(A{row},"dddd"))'

    # === Hidden sheet for lookup lists ===
    ws_lists = wb.create_sheet(title="Lists")

    # --- Courses ---
    courses = (
        db.session.query(Course)
        .outerjoin(Exam, Course.courseExamId == Exam.examId)
        .filter(
            and_(
                Course.courseStatus == True,
                or_(
                    Exam.examStartTime.is_(None),
                    Exam.examEndTime.is_(None)
                )
            )
        )
        .all()
    )
    for i, c in enumerate(courses, start=1):
        ws_lists[f"A{i}"] = c.courseCodeSectionIntake   # Course/Sec
        ws_lists[f"B{i}"] = c.courseDepartment          # Program
        ws_lists[f"C{i}"] = c.practicalLecturer.userId if c.practicalLecturer else ""  # Lecturer
        ws_lists[f"D{i}"] = c.courseStudent or 0        # No of students

    # --- Venues ---
    venues = Venue.query.all()
    for i, v in enumerate(venues, start=1):
        ws_lists[f"G{i}"] = v.venueNumber   # put venues in column G

    # === Data Validations ===s
    if courses:
        dv_course = DataValidation(
            type="list",
            formula1=f"=Lists!$A$1:$A${len(courses)}",
            allow_blank=False
        )
        ws.add_data_validation(dv_course)
        dv_course.add("F3:F1002")  # Course/Sec dropdown

        # Auto-fill program, lecturers, no of students
        for row in range(3, 503):
            ws[f"E{row}"] = f'=IF(F{row}="","",VLOOKUP(F{row},Lists!$A$1:$D${len(courses)},2,FALSE))'  # Program
            ws[f"G{row}"] = f'=IF(F{row}="","",VLOOKUP(F{row},Lists!$A$1:$D${len(courses)},3,FALSE))'  # Lecturer
            ws[f"H{row}"] = f'=IF(F{row}="","",VLOOKUP(F{row},Lists!$A$1:$D${len(courses)},4,FALSE))'  # No of Students

    if venues:
        dv_venue = DataValidation(
            type="list",
            formula1=f"=Lists!$G$1:$G${len(venues)}",
            allow_blank=False
        )
        ws.add_data_validation(dv_venue)
        dv_venue.add("I3:I1002")  # Room dropdown

    ws_lists.sheet_state = 'hidden'

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# -------------------------------
# Function for Admin ManageExam Download Excel File Template
# -------------------------------
@app.route('/download_exam_template')
@login_required
def download_exam_template():
    output = generate_manageexam_template()
    return send_file(
        output,
        as_attachment=True,
        download_name="ManageExam.xlsx", # type: ignore[arg-type]
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------------
# Function for Admin ManageExam Route Upload File Combine Date and Time
# -------------------------------
def process_exam_row(row):
    examDate = row['date']
    if isinstance(examDate, str):
        examDate = datetime.strptime(examDate.strip(), "%Y-%m-%d %H:%M:%S")
        
    examDate_text = examDate.strftime("%Y-%m-%d")
    startTime_text = row['start']
    endTime_text   = row['end']

    if not examDate_text or not startTime_text or not endTime_text:
        return False, "Invalid time/date"
    
    start_dt = datetime.combine(examDate.date(), datetime.strptime(startTime_text, "%H:%M:%S").time())
    end_dt   = datetime.combine(examDate.date(), datetime.strptime(endTime_text, "%H:%M:%S").time())
    venue = str(row['room']).upper()

    # Conflict check before saving
    conflict = VenueExam.query.filter(
        VenueExam.venueNumber == venue,
        VenueExam.startDateTime < end_dt + timedelta(minutes=30),
        VenueExam.endDateTime > start_dt - timedelta(minutes=30)
    ).first()

    if conflict:
        return None, ''

    # No conflict → create
    create_exam_and_related(start_dt, end_dt, str(row['course/sec']).upper(), venue, str(row['lecturer']).upper(), None, None)
    return True, ''


# -------------------------------
# Get ExamDetails for ManageExamEditPage
# -------------------------------
@app.route('/get_exam_details/<path:course_code_section>')
@login_required
def get_exam_details(course_code_section):
    course = Course.query.filter_by(courseCodeSectionIntake=course_code_section).first()
    if not course:
        return jsonify({"error": "Course not found"}), 404

    exam = Exam.query.filter_by(examId=course.courseExamId).first() if course.courseExamId else None
    venues = VenueExam.query.filter_by(examId=exam.examId).all() if exam else []

    response_data = {
        "courseCodeSection": course.courseCodeSectionIntake,
        "courseName": course.courseName or "",
        "courseDepartment": course.courseDepartment or "",
        "practicalLecturer": course.practicalLecturer.userName if course.practicalLecturer else "",
        "tutorialLecturer": course.tutorialLecturer.userName if course.tutorialLecturer else "",
        "courseStudent": course.courseStudent or 0,
        "examVenues": [v.venueNumber for v in venues],
        "examStartTime": exam.examStartTime.strftime("%Y-%m-%dT%H:%M") if exam and exam.examStartTime else "",
        "examEndTime": exam.examEndTime.strftime("%Y-%m-%dT%H:%M") if exam and exam.examEndTime else "",
        "examNoInvigilator": exam.examNoInvigilator if exam else 0
    }
    return jsonify(response_data)


# -------------------------------
# Reformat the datetime for ManageExamEditPage
# -------------------------------
def parse_datetime(date_str, time_str):
    raw = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized datetime format: {raw}")

# -------------------------------
# Get VenueDetails for ManageExamEditPage
# -------------------------------
@app.route('/get_available_venues', methods=['POST'])
@login_required
def get_available_venues():
    start_date = request.form.get('startDate', '').strip()
    start_time = request.form.get('startTime', '').strip()
    end_date = request.form.get('endDate', '').strip()
    end_time = request.form.get('endTime', '').strip()

    if not all([start_date, start_time, end_date, end_time]):
        return jsonify({'venues': []})

    start_dt = parse_datetime(start_date, start_time)
    end_dt = parse_datetime(end_date, end_time)

    if not start_dt or not end_dt:
        return jsonify({'venues': []})

    # Get all venues
    all_venues = Venue.query.all()
    available_venues = []

    for venue in all_venues:
        # Check for any conflict in VenueExam
        conflict = VenueExam.query.filter(
            VenueExam.venueNumber == venue.venueNumber,
            VenueExam.startDateTime < end_dt + timedelta(minutes=30),
            VenueExam.endDateTime > start_dt - timedelta(minutes=30),
        ).first()

        if not conflict:
            available_venues.append(venue.venueNumber)

    return jsonify({'venues': available_venues})

# -------------------------------
# Reassign invigilator for ManageExamEditPage
# -------------------------------
def adjust_exam(exam, new_start, new_end, new_invigilator_count, new_venues):
    old_start = exam.examStartTime
    old_end = exam.examEndTime

    # 1️⃣ Update exam times
    exam.examStartTime = new_start
    exam.examEndTime = new_end
    exam.examNoInvigilator = new_invigilator_count

    db.session.flush()  # Ensure exam is updated before attendance

    # Calculate new duration and old duration
    new_hours = (new_end - new_start).total_seconds() / 3600.0
    old_hours = (old_end - old_start).total_seconds() / 3600.0 if old_start and old_end else 0

    # 2️⃣ Update invigilators
    report = InvigilationReport.query.filter_by(examId=exam.examId).first()
    if report:
        current_attendances = report.attendances
        current_count = len(current_attendances)

        # Adjust pending hours if time changed
        for att in current_attendances:
            inv = att.invigilator
            if inv:
                inv.userPendingCumulativeHours = max(
                    0.0,
                    (inv.userPendingCumulativeHours or 0.0) - old_hours + new_hours
                )

        # Add new invigilators if count increased
        if new_invigilator_count > current_count:
            extra_needed = new_invigilator_count - current_count
            assigned_ids = [att.invigilatorId for att in current_attendances]

            # Exclude lecturers
            lecturers = [exam.course.coursePractical, exam.course.courseTutorial]

            eligible = User.query.filter(
                User.userLevel == 1,
                User.userStatus == 1,
                ~User.userId.in_(assigned_ids + lecturers)
            ).all()

            # Filter by max 36 hours
            eligible = [u for u in eligible if (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0) < 36]

            # Split by gender
            males = sorted([u for u in eligible if u.userGender == "MALE"], key=lambda u: (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0))
            females = sorted([u for u in eligible if u.userGender == "FEMALE"], key=lambda u: (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0))

            chosen = []
            if extra_needed >= 2:
                if males:
                    chosen.append(males.pop(0))
                if females and len(chosen) < extra_needed:
                    chosen.append(females.pop(0))
                extra_needed -= len(chosen)

            pool = sorted(males + females, key=lambda u: (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0))
            chosen += pool[:extra_needed]

            # Assign to report
            for inv in chosen:
                inv.userPendingCumulativeHours = (inv.userPendingCumulativeHours or 0.0) + new_hours
                db.session.add(InvigilatorAttendance(
                    reportId=report.invigilationReportId,
                    invigilatorId=inv.userId,
                    timeCreate=datetime.now(timezone.utc)
                ))

        # Remove excess invigilators if count decreased
        elif new_invigilator_count < current_count:
            remove_count = current_count - new_invigilator_count
            to_remove = random.sample(current_attendances, remove_count)
            for att in to_remove:
                inv = att.invigilator
                if inv:
                    inv.userPendingCumulativeHours = max(0, (inv.userPendingCumulativeHours or 0) - new_hours)
                db.session.delete(att)

    else:
        # Create report if doesn't exist
        report = InvigilationReport(examId=exam.examId)
        db.session.add(report)
        db.session.flush()

        # Assign invigilators for this new exam
        new_hours = (new_end - new_start).total_seconds() / 3600.0

        eligible = User.query.filter(
            User.userLevel == 1,
            User.userStatus == 1
        ).all()

        # Filter by max 36 hours
        eligible = [u for u in eligible if (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0) < 36]

        males = sorted([u for u in eligible if u.userGender == "MALE"], key=lambda u: (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0))
        females = sorted([u for u in eligible if u.userGender == "FEMALE"], key=lambda u: (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0))

        chosen = []
        if new_invigilator_count >= 2:
            if males:
                chosen.append(males.pop(0))
            if females and len(chosen) < new_invigilator_count:
                chosen.append(females.pop(0))

        pool = sorted(males + females, key=lambda u: (u.userCumulativeHours or 0) + (u.userPendingCumulativeHours or 0))
        chosen += pool[:(new_invigilator_count - len(chosen))]

        for inv in chosen:
            inv.userPendingCumulativeHours = (inv.userPendingCumulativeHours or 0.0) + new_hours
            db.session.add(InvigilatorAttendance(
                reportId=report.invigilationReportId,
                invigilatorId=inv.userId,
                timeCreate=datetime.now(timezone.utc)
            ))


    # 3️⃣ Update venue(s)
    # Get old venue records
    old_records = {v.venueNumber: v for v in VenueExam.query.filter_by(examId=exam.examId).all()}
    used_venues = set()
    remaining_students = exam.course.courseStudent

    for venue_no in new_venues:
        venue_obj = Venue.query.filter_by(venueNumber=venue_no).first()
        if not venue_obj:
            continue

        # Skip if already used
        if venue_no in old_records:
            rec = old_records[venue_no]
            rec.startDateTime = new_start
            rec.endDateTime = new_end
            rec.capacity = min(rec.capacity, remaining_students)
            used_venues.add(venue_no)
            remaining_students -= rec.capacity
            continue

        # Check conflicts
        conflict = VenueExam.query.filter(
            VenueExam.venueNumber == venue_no,
            VenueExam.examId != exam.examId,
            VenueExam.startDateTime < new_end,
            VenueExam.endDateTime > new_start
        ).first()
        if conflict:
            raise ValueError(f"{venue_no} conflicts with another exam {conflict.startDateTime}-{conflict.endDateTime}")

        allocated = min(venue_obj.venueCapacity, remaining_students)
        remaining_students -= allocated

        new_ve = VenueExam(
            examId=exam.examId,
            venueNumber=venue_no,
            startDateTime=new_start,
            endDateTime=new_end,
            capacity=allocated
        )
        db.session.add(new_ve)
        used_venues.add(venue_no)

    # Remove old venues no longer used
    for venue_no, rec in old_records.items():
        if venue_no not in used_venues:
            db.session.delete(rec)

    if remaining_students > 0:
        raise ValueError(f"{remaining_students} students could not be seated")

    db.session.commit()


# -------------------------------
# Function for Admin ManageExam Route
# -------------------------------
@app.route('/admin/manageExam', methods=['GET', 'POST'])
@login_required
def admin_manageExam():
    # Auto-expire exams
    now = datetime.now() + timedelta(hours=8)
    expired_exams = Exam.query.filter(Exam.examEndTime < now, Exam.examStatus == True).all()
    for exam in expired_exams:
        exam.examStatus = False
    db.session.commit()

    # Load departments and exams
    department_data = Department.query.all()
    exam_data_query = Exam.query.join(Exam.course).filter(Course.courseStatus == True)
    exam_data = (
        exam_data_query
        .order_by(
            Exam.examStatus.desc(),
            case((Exam.examStartTime == None, 0), else_=1).asc(),  # NULLs first
            Exam.examStartTime.desc(),
            Exam.examId.asc()
        )
        .all()
    )
    display_exam_data = [e for e in exam_data if e.examStatus]
    total_exam_activated = Exam.query.filter(
        Exam.examStatus == 1,
        Exam.examStartTime.isnot(None)
    ).count()

    # For edit section
    exam_selected_code = request.form.get('editExamCourseSection')
    course = Course.query.filter_by(courseCodeSectionIntake=exam_selected_code).first()
    exam_select = Exam.query.filter_by(examId=course.courseExamId).first() if course else None
    venue_data = Venue.query.order_by(Venue.venueCapacity.asc()).all()

    # Counters
    unassigned_exam = len([e for e in exam_data if e.examStatus and e.examStartTime is None])
    complete_exam = len([
        e for e in exam_data if e.examStatus and e.examStartTime and e.examEndTime and e.examNoInvigilator not in (None, 0)
    ])

    # Default form values
    invigilatorNo_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # 1️⃣ Upload exam file (optional)
        if form_type == 'upload':
            return handle_file_upload(
                file_key='exam_file',
                expected_cols=['date', 'day', 'start', 'end', 'program','course/sec','lecturer','no of','room'],
                process_row_fn=process_exam_row,
                redirect_endpoint='admin_manageExam',
                usecols="A:I",
                skiprows=1 
            )

        # 2️⃣ Edit exam
        elif form_type == 'edit' and exam_select:
            action = request.form.get('action')
            start_date_raw = request.form.get('startDate', '').strip()
            start_time_raw = request.form.get('startTime', '').strip()
            end_date_raw = request.form.get('endDate', '').strip()
            end_time_raw = request.form.get('endTime', '').strip()
            start_dt = parse_datetime(start_date_raw, start_time_raw)
            end_dt = parse_datetime(end_date_raw, end_time_raw)
            venue_list = request.form.getlist("venue[]")
            invigilatorNo_text = request.form.get('invigilatorNo', '0').strip()
            new_inv_count = int(invigilatorNo_text)

            if action == 'update':
                try:
                    adjust_exam(
                        exam=exam_select,
                        new_start=start_dt,
                        new_end=end_dt,
                        new_invigilator_count=new_inv_count,
                        new_venues=venue_list
                    )
                    flash(f"💾 Exam {exam_select.course.courseCodeSectionIntake} updated successfully.", "success")
                except ValueError as e:
                    db.session.rollback()
                    flash(str(e), "error")
                    flash("❌ Please reselect venues and try again.", "error")
                    return redirect(request.url)
                except Exception as e:
                    db.session.rollback()
                    flash(f"⚠️ Unexpected error: {str(e)}", "error")
                    flash("❌ Please reselect venues and try again.", "error")
                    return redirect(request.url)

            elif action == 'delete':
                # Delete all invigilators and reports
                noInvigilator = exam_select.course.courseStudent
                reports = InvigilationReport.query.filter_by(examId=exam_select.examId).all()
                for report in reports:
                    for att in report.attendances:
                        if exam_select.examStartTime and exam_select.examEndTime:
                            duration = (exam_select.examEndTime - exam_select.examStartTime).total_seconds() / 3600.0
                            user = User.query.get(att.invigilatorId)
                            if user:
                                user.userPendingCumulativeHours = max(0, user.userPendingCumulativeHours - duration)
                        db.session.delete(att)
                    db.session.delete(report)

                # Delete venues
                for ve in VenueExam.query.filter_by(examId=exam_select.examId).all():
                    db.session.delete(ve)

                exam_select.examStartTime = None
                exam_select.examEndTime = None
                if noInvigilator > 32:
                    exam_select.examNoInvigilator = 3
                else:
                    exam_select.examNoInvigilator = 2
                db.session.commit()
                flash(f"🗑️ Exam {exam_select.course.courseCodeSectionIntake} deleted successfully.", "success")

            return redirect(url_for('admin_manageExam'))

    return render_template(
        'admin/adminManageExam.html',
        active_tab='admin_manageExamtab',
        exam_data=exam_data,
        unassigned_exam=unassigned_exam,
        display_exam_data=display_exam_data,
        venue_data=venue_data,
        department_data=department_data,
        complete_exam=complete_exam,
        exam_select=exam_select,
        total_exam_activated=total_exam_activated
    )



# -------------------------------
# Function for Admin User Download Excel Template
# -------------------------------
def generate_user_template():
    warnings.simplefilter("ignore", UserWarning)
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None, "Workbook has no active worksheet"
    ws.title = "Users"

    # First row empty
    ws.append([])
    # Second row = headers
    headers = ['Id', 'CardId', 'Name', 'Department', 'Role', 'Email', 'Contact', 'Gender']
    ws.append(headers)

    # === Hidden sheet for lookup lists ===
    ws_lists = wb.create_sheet(title="Lists")

    # --- Departments ---
    departments = Department.query.all()
    for i, d in enumerate(departments, start=1):
        ws_lists[f"A{i}"] = d.departmentCode

    # --- Roles ---
    roles = ["Lecturer", "Dean", "HOS", "HOP", "Admin"]
    for i, r in enumerate(roles, start=1):
        ws_lists[f"B{i}"] = r

    # --- Gender ---
    genders = ["Male", "Female"]
    for i, g in enumerate(genders, start=1):
        ws_lists[f"C{i}"] = g

    # === Data Validations ===
    if departments:
        dv_department = DataValidation(
            type="list",
            formula1=f"=Lists!$A$1:$A${len(departments)}",
            allow_blank=False
        )
        ws.add_data_validation(dv_department)
        dv_department.add("D3:D1002")  # Department dropdown

    dv_role = DataValidation(
        type="list",
        formula1=f"=Lists!$B$1:$B${len(roles)}",
        allow_blank=False
    )
    ws.add_data_validation(dv_role)
    dv_role.add("E3:E1002")  # Role dropdown

    dv_gender = DataValidation(
        type="list",
        formula1=f"=Lists!$C$1:$C${len(genders)}",
        allow_blank=False
    )
    ws.add_data_validation(dv_gender)
    dv_gender.add("H3:H1002")  # Gender dropdown

    ws_lists.sheet_state = 'hidden'
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# -------------------------------
# Route to download User Excel template
# -------------------------------
@app.route('/download_user_template')
@login_required
def download_user_template():
    output = generate_user_template()
    return send_file(
        output,
        as_attachment=True,
        download_name="UserTemplate.xlsx",  # type: ignore[arg-type]
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
    role_mapping = {'lecturer': 1, 'dean': 2, 'hos': 3, 'hop': 4, 'admin': 5}
    hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')

    # Handle empty cardid properly
    cardid = row.get('cardid')
    if pd.isna(cardid) or str(cardid).strip().lower() in ["", "nan", "none"]:
        cardid = None
    else:
        cardid = str(cardid).upper()

    return create_staff(
        id=str(row['id']).upper(),
        department=str(row['department']).upper(),
        name=str(row['name']).upper(),
        role=role_mapping.get(str(row['role']).strip().lower()),
        email=str(row['email']),
        contact=clean_contact(row['contact']),
        gender=str(row['gender']).upper(),
        hashed_pw=hashed_pw,
        cardId=cardid,  # use the cleaned value
    )

# -------------------------------
# Read All StaffDetails Under The ManageLecturerEditPage
# -------------------------------
@app.route('/get_staff/<id>')
@login_required
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
        "userStatus": str(user.userStatus),
        "userCardId": user.userCardId or ""
    })

# -------------------------------
# Function for Admin ManageStaff Route
# -------------------------------
@app.route('/admin/manageStaff', methods=['GET', 'POST'])
@login_required
def admin_manageStaff():
    user_data = User.query.order_by(func.field(User.userStatus, 1, 0, 2), User.userLevel.desc()).all()
    department_data = Department.query.all()

    # === Dashboard Counts ===
    total_staff = User.query.count()
    total_admin = User.query.filter_by(userLevel=5).count()
    total_hop = User.query.filter_by(userLevel=4).count()
    total_hos = User.query.filter_by(userLevel=3).count()
    total_dean = User.query.filter_by(userLevel=2).count()
    total_lecturer = User.query.filter_by(userLevel=1).count()
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
                expected_cols=['id', 'cardid', 'name', 'department', 'role', 'email', 'contact', 'gender'],
                process_row_fn=process_staff_row,
                redirect_endpoint='admin_manageStaff',
                usecols="A:H",
                skiprows=1 
            )

        elif form_type == 'edit':
            action = request.form.get('action')
            if action == 'update' and user_select:
                user_select.userName = request.form['editUsername']
                user_select.userEmail = request.form['editEmail']
                user_select.userContact = request.form['editContact']
                user_select.userGender = request.form['editGender']
                user_select.userLevel = int(request.form['editRole'])
                user_select.userStatus = int(request.form['editStatus'])
                user_select.userCardId = request.form['editCardId']
                new_department_code = request.form['editDepartment']

                if user_select.userStatus == 2:
                    user_select.userRegisterDateTime = datetime.now(timezone.utc)

                if user_select.userDepartment != new_department_code:
                    # 1. Remove user from OLD department
                    old_department = Department.query.filter_by(departmentCode=user_select.userDepartment).first()
                    if old_department:
                        if old_department.hopId == user_select.userId:
                            old_department.hopId = None
                        if old_department.deanId == user_select.userId:
                            old_department.deanId = None
                        if old_department.hosId == user_select.userId:
                            old_department.hosId = None

                    # 2. Assign user to NEW department
                    new_department = Department.query.filter_by(departmentCode=new_department_code).first()
                    if new_department:
                        if user_select.userLevel == 3:  # HOS
                            new_department.hosId = user_select.userId
                        elif user_select.userLevel == 4:  # HOP
                            new_department.hopId = user_select.userId
                        elif user_select.userLevel == 2:  # Dean
                            new_department.deanId = user_select.userId

                    # 3. Update user table
                    user_select.userDepartment = new_department_code
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
                "cardId": request.form.get('cardId', '').strip(),
            }
            success, message = create_staff(**form_data)
            if success:
                # Send verification email
                email_success, email_message = send_verifyActivateLink(form_data["email"])
                if email_success:
                    flash("Staff account created and verification link sent!", "success")
                else:
                    flash(f"Staff account created but failed to send verification email: {email_message}", "error")
            else:
                flash(message, "error")
            return redirect(url_for('admin_manageStaff'))

    return render_template(
        'admin/adminManageStaff.html',
        active_tab='admin_manageStafftab',
        user_data=user_data,
        department_data=department_data,
        total_staff=total_staff,
        total_admin=total_admin,
        total_hop=total_hop,
        total_hos=total_hos,
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


def parse_date_range(date_range):
    """Parse classWeekDate 'MM/DD/YYYY-MM/DD/YYYY' and return (start, end) datetime safely."""
    if not date_range:
        return None, None
    try:
        # Split only on the last hyphen in case there are others in the string
        start_str, end_str = date_range.rsplit("-", 1)
        start = datetime.strptime(start_str.strip(), "%m/%d/%Y")
        end = datetime.strptime(end_str.strip(), "%m/%d/%Y")
        return start, end
    except Exception as e:
        print(f"Date parse error for '{date_range}': {e}")
        return None, None


# -------------------------------
# Get TimetableLink Details for ManageTimetableEditPage
# -------------------------------
@app.route('/get_linkTimetable/<path:timetableID>')
@login_required
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
        return 

    # Normalize the lecturer input: remove all spaces
    normalized_lecturer = ''.join(lecturer.split())

    # Find user where username with spaces removed matches normalized lecturer
    user = User.query.filter(func.replace(User.userName, " ", "") == normalized_lecturer).first()

    # Ensure timetable exists for user
    if user:
        timetable = Timetable.query.filter_by(user_id=user.userId).first()
        if not timetable:
            timetable = Timetable(user_id=user.userId)
            db.session.add(timetable)
            db.session.commit()
    else:
        timetable = None

    # ---- Delete old rows if lecturer already exists in DB ----
    existing_rows = TimetableRow.query.filter_by(lecturerName=lecturer).count()
    if existing_rows > 0:
        TimetableRow.query.filter_by(lecturerName=lecturer).delete()
        db.session.commit()

    # ---- Insert new rows from structured data ----
    rows_inserted = 0

    for day, activities in structured["days"].items():
        for act in activities:
            if not (act.get("class_type") and act.get("time") and act.get("room") and act.get("course")):
                continue
            if act.get("sections"):
                for sec in act["sections"]:
                    if not (sec.get("intake") and sec.get("course_code") and sec.get("section")):
                        continue

                    new_row = TimetableRow(
                        timetable_id=timetable.timetableId if timetable else None,
                        filename=filename,
                        lecturerName=lecturer,
                        classType=act.get("class_type"),
                        classDay=day,
                        classTime=act.get("time"),
                        classRoom=act.get("room"),
                        courseName=act.get("course"),
                        courseIntake=sec.get("intake"),
                        courseCode=sec.get("course_code"),
                        courseSection=sec.get("section"),
                        classWeekRange=",".join(act.get("weeks_range", [])) if act.get("weeks_range") else None,
                        classWeekDate=act.get("weeks_date"),
                    )
                    db.session.add(new_row)
                    rows_inserted += 1

    db.session.commit()
    return rows_inserted


# -------------------------------
# Function for Admin ManageTimetable Route
# -------------------------------
@app.route('/admin/manageTimetable', methods=['GET', 'POST'])
@login_required
def admin_manageTimetable():
    department_data = Department.query.all()
    selected_department = request.args.get("department")
    selected_lecturer = request.args.get("lecturer")

    # Base query
    timetable_data_query = (
        TimetableRow.query
        .join(Timetable, TimetableRow.timetable_id == Timetable.timetableId)
        .join(User, Timetable.user_id == User.userId)
        .filter(User.userStatus == 1)  # active staff only
    )

    # Department filter
    if selected_department:
        timetable_data_query = timetable_data_query.filter(User.userDepartment == selected_department)
    # Lecturer filter (by userId)
    if selected_lecturer:
        timetable_data_query = timetable_data_query.filter(TimetableRow.lecturerName == selected_lecturer)


    timetable_data = timetable_data_query.order_by(TimetableRow.rowId.asc()).all()
    lecturers = sorted({row.lecturerName for row in timetable_data})
    total_timetable = db.session.query(func.count(func.distinct(TimetableRow.lecturerName))).scalar()
    timetable_list = Timetable.query.filter(Timetable.timetableId != None).all()
    
    timetable_select = None
    timetable_selected = request.form.get('editTimetableList')
    if timetable_selected:
        timetable_select = Timetable.query.filter_by(timetableId=timetable_selected).first()
    timetable_map = {t.user_id: t.timetableId for t in timetable_list}

    # Staff list (exclude certain levels/status)
    staff_all  = User.query.filter(
        User.userLevel != 5,
        User.userStatus != 2
    ).all()
    unassigned_staff_list = [staff for staff in staff_all if staff.userId not in timetable_map]
    staff_list = staff_all

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

    # ---- POST Handling ----
    if request.method == "POST":
        form_type = request.form.get('form_type')

        # --- Upload timetable PDF files ---
        if form_type == 'upload':
            files = request.files.getlist("timetable_file[]")
            latest_files = {}
            skipped_files = []

            # Keep only the latest file per lecturer
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

            total_rows_inserted = 0
            total_files_processed = 0

            # Process each latest file
            for base_name, (timestamp, file) in latest_files.items():
                reader = PyPDF2.PdfReader(file.stream)
                raw_text = "".join(page.extract_text() + " " for page in reader.pages if page.extract_text())
                structured = parse_timetable(raw_text)
                structured['filename'] = file.filename
                rows_inserted = save_timetable_to_db(structured)

                if (rows_inserted or 0) > 0:
                    total_files_processed += 1
                    total_rows_inserted += rows_inserted or 0
            flash(f"Files read: {len(files)}, Processed: {total_files_processed}, Rows inserted: {total_rows_inserted}, Files skipped: {len(skipped_files)}", "success")
            return redirect(url_for('admin_manageTimetable'))

        # --- Manual link timetable to staff ---
        elif form_type == 'manual':
            user_id = request.form.get("staffList")
            lecturer = request.form.get("lecturerName")

            if user_id and lecturer:
                timetable = Timetable.query.filter_by(user_id=user_id).first()
                if not timetable:
                    timetable = Timetable(user_id=user_id)
                    db.session.add(timetable)
                    db.session.commit()

                rows = TimetableRow.query.filter_by(lecturerName=lecturer, timetable_id=None).all()
                for row in rows:
                    row.timetable_id = timetable.timetableId

                db.session.commit()
                flash(f"Timetable for {lecturer} has been successfully linked to Staff ID {user_id}.", "success")
            else:
                flash("Missing lecturer or staff", "error")
            return redirect(url_for('admin_manageTimetable'))

        # --- Edit / Delete timetable link ---
        elif form_type == 'edit':
            action = request.form.get('action')
            if action == 'update' and timetable_select:
                new_user_id = request.form['editStaffList']

                if str(timetable_select.user_id) == new_user_id:
                    flash("No changes made. Timetable already linked to this staff.", "success")
                else:
                    existing = Timetable.query.filter(
                        Timetable.user_id == new_user_id,
                        Timetable.timetableId != timetable_select.timetableId
                    ).first()

                    if existing:
                        flash(f"Staff ID:{new_user_id} is already linked to another timetable(ID:{existing.timetableId}).", "error")
                    else:
                        timetable_select.user_id = new_user_id
                        db.session.commit()
                        flash("Timetable updated successfully.", "success")

            elif action == 'delete' and timetable_select:
                db.session.delete(timetable_select)
                db.session.commit()
                flash("Timetable deleted successfully.", "success")
                return redirect(url_for('admin_manageTimetable'))

    return render_template('admin/adminManageTimetable.html',active_tab='admin_manageTimetabletab',timetable_data=timetable_data,lecturers=lecturers,selected_lecturer=selected_lecturer,
        department_data=department_data,selected_department=selected_department,unassigned_staff_list=unassigned_staff_list,total_timetable=total_timetable,unassigned_summary=unassigned_summary,staff_list=staff_list,
        **day_counts,timetable_list=timetable_list,timetable_map=timetable_map,timetable_select=timetable_select)




# -------------------------------
# Function for Admin ManageInviglationTimetable Route (Simple Calendar View + Overnight Handling)
# -------------------------------
def get_calendar_data():
    attendances = get_all_attendances()
    calendar_data = defaultdict(list)
    seen_exams = set()  # ✅ To skip duplicate exam sessions

    for att in attendances:
        exam = att.report.exam

        # Skip if this exam already processed
        if exam.examId in seen_exams:
            continue
        seen_exams.add(exam.examId)

        start_dt = exam.examStartTime
        end_dt = exam.examEndTime
        start_date = start_dt.date()
        end_date = end_dt.date()
        is_overnight = start_date != end_date and exam.examStatus == True
        venues = exam.venue_availabilities

        def exam_dict(start, end):
            return {
                "exam_id": exam.examId,
                "course_name": exam.course.courseName,
                "course_code": exam.course.courseCodeSectionIntake,
                "start_time": start,
                "end_time": end,
                "status": exam.examStatus,
                "is_overnight": is_overnight,
                "venue": [{"venueNumber": v.venueNumber, "capacity": v.capacity} for v in venues],
            }

        if is_overnight:
            # Part 1: From start time to 23:59 on start day
            calendar_data[start_date].append(
                exam_dict(start_dt, datetime.combine(start_date, datetime.max.time()).replace(hour=23, minute=59))
            )
            # Part 2: From 00:00 on next day to end time
            calendar_data[end_date].append(
                exam_dict(datetime.combine(end_date, datetime.min.time()), end_dt)
            )
        else:
            # Normal same-day exam
            calendar_data[start_date].append(exam_dict(start_dt, end_dt))

    calendar_data = dict(sorted(calendar_data.items()))
    return calendar_data


# -------------------------------
# Function for Admin ManageInviglationTimetable Route
# -------------------------------
@app.route('/admin/manageInvigilationTimetable', methods=['GET'])
@login_required
def admin_manageInvigilationTimetable():
    calendar_data = get_calendar_data()
    return render_template('admin/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', calendar_data=calendar_data)




# -------------------------------
# Calculate All InvigilatorAttendance and InvigilationReport Data From Database
# -------------------------------
def calculate_invigilation_stats():
    base_query = (
        db.session.query(InvigilationReport)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(InvigilatorAttendance, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .distinct()
    )

    total_report = base_query.count()
    total_active_report = base_query.filter(Exam.examStatus == True).count()

    # Pull all attendance records for detailed time analysis
    query = (
        db.session.query(
            InvigilatorAttendance.attendanceId,
            InvigilatorAttendance.invigilatorId,
            InvigilatorAttendance.checkIn,
            InvigilatorAttendance.checkOut,
            Exam.examStartTime,
            Exam.examEndTime,
            InvigilatorAttendance.reportId
        )
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .filter(InvigilatorAttendance.invigilationStatus == True)
        .all()
    )

    stats = {
        "total_report": total_report,
        "total_activeReport": total_active_report,
        "total_checkInLate": 0,
        "total_checkOutEarly": 0,
    }

    for row in query:
        if row.checkIn and row.checkIn > row.examStartTime:
            stats["total_checkInLate"] += 1
        if row.checkOut and row.checkOut < row.examEndTime:
            stats["total_checkOutEarly"] += 1
    return stats


# -------------------------------
# Read All InvigilatorAttendance Data From Database
# -------------------------------
def get_all_attendances():
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .order_by(Exam.examStatus.desc(), Exam.examStartTime.desc())
        .all()
    )


# -------------------------------
# Helper: Parse Date + Time from Excel
# -------------------------------
def parse_attendance_datetime(date_val, time_val):
    """Combine date + time from Excel into datetime object."""
    try:
        # Parse date
        if isinstance(date_val, datetime):
            date_part = date_val.date()
        else:
            date_str = str(date_val).strip()
            try:
                # Try DD/MM/YYYY first
                date_part = datetime.strptime(date_str, "%d/%m/%Y").date()
            except ValueError:
                # Try ISO format YYYY-MM-DD
                date_part = datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
        
        # Parse time
        if isinstance(time_val, datetime):
            time_part = time_val.time()
        else:
            time_str = str(time_val).strip()
            if ':' in time_str:
                parts = time_str.split(":")
                if len(parts) == 2:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    time_part = datetime.strptime(f"{hours:02d}:{minutes:02d}:00", "%H:%M:%S").time()
                elif len(parts) == 3:
                    time_part = datetime.strptime(time_str, "%H:%M:%S").time()
                else:
                    raise ValueError(f"Invalid time format: {time_str}")
            else:
                raise ValueError(f"Invalid time format: {time_str}")
        
        return datetime.combine(date_part, time_part)
    
    except Exception as e:
        flash(f"Error parsing datetime: {e}", "error")
        return None


# -------------------------------
# Process Single Attendance Row
# -------------------------------
def process_attendance_row(row):
    try:
        # 1. Extract UID
        raw_uid = str(row['card iud']).upper().replace('UID:', '').strip()

        # 2. Find matching user
        user = User.query.filter_by(userCardId=raw_uid).first()
        if not user:
            return False, f"No matching user for UID {raw_uid}"

        # 3. Parse datetime
        dt_obj = parse_attendance_datetime(row['date'], row['time'])
        if not dt_obj:
            return False, f"Invalid date/time format: {row['date']} {row['time']}"

        # 4. Determine in/out value
        inout_val = str(row['in/out']).lower().strip()
        if inout_val not in ['in', 'out']:
            return False, f"Invalid in/out value: {row['in/out']}"

        # 5. Skip duplicate
        if inout_val == 'in':
            existing = InvigilatorAttendance.query.filter_by(
                invigilatorId=user.userId,
                checkIn=dt_obj
            ).first()
        else:
            existing = InvigilatorAttendance.query.filter_by(
                invigilatorId=user.userId,
                checkOut=dt_obj
            ).first()

        if existing:
            return False, f"Duplicate entry skipped for {user.userName} at {dt_obj} ({inout_val.upper()})"

        # 6. Proceed with updating attendance
        attendances = InvigilatorAttendance.query \
            .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId) \
            .join(Exam, InvigilationReport.examId == Exam.examId) \
            .filter(InvigilatorAttendance.invigilatorId == user.userId) \
            .all()
        
        if not attendances:
            return False, f"No invigilation sessions found for user {user.userName} near {dt_obj}"

        updated_count = 0
        for attendance in attendances:
            exam = Exam.query.get(attendance.report.examId)
            if not exam:
                continue

            exam_start = exam.examStartTime
            exam_end = exam.examEndTime

            if not (exam_start - timedelta(hours=1) <= dt_obj <= exam_end + timedelta(hours=1)):
                continue

            if inout_val == "in":
                if attendance.checkIn is None:
                    attendance.checkIn = dt_obj
                    attendance.remark = "CHECK IN" if dt_obj <= exam_start else "CHECK IN LATE"
                    updated_count += 1
            elif inout_val == "out":
                if attendance.checkOut is None:
                    attendance.checkOut = dt_obj
                    if attendance.checkIn:
                        actual_checkin = attendance.checkIn
                        checkin_for_hours = actual_checkin if attendance.remark == "CHECK IN LATE" else exam_start
                        checkout_for_hours = dt_obj if dt_obj < exam_end else exam_end
                        hours_worked = (checkout_for_hours - checkin_for_hours).total_seconds() / 3600
                        user.userCumulativeHours += hours_worked
                        attendance.remark = "COMPLETED" if dt_obj >= exam_end else "CHECK OUT EARLY"
                    else:
                        attendance.remark = "PENDING"
                    updated_count += 1

        if updated_count > 0:
            db.session.commit()
            return True, f"Attendance updated for {user.userName} ({updated_count} record(s))"
        else:
            return False, f"No attendance sessions updated for {user.userName} at {dt_obj}"

    except Exception as e:
        db.session.rollback()
        return False, f"Error processing row: {e}"




# -------------------------------
# Admin Route
# -------------------------------
@app.route('/admin/manageInvigilationReport', methods=['GET', 'POST'])
@login_required
def admin_manageInvigilationReport():
    attendances = get_all_attendances()
    stats = calculate_invigilation_stats()

    # Attach composite key for sorting/grouping
    for att in attendances:
        report = att.report
        exam = Exam.query.get(report.examId) if report else None
        att.group_key = (not exam.examStatus if exam else True, exam.examStartTime if exam else datetime.min)

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # Upload Section
        if form_type == 'upload':
            return handle_file_upload(
                file_key='attendance_file',
                expected_cols=['card iud', 'name', 'date', 'time', 'in/out'],
                process_row_fn=process_attendance_row,
                redirect_endpoint='admin_manageInvigilationReport',
                usecols="A:E",
                skiprows=0
            )

    return render_template('admin/adminManageInvigilationReport.html', active_tab='admin_manageInvigilationReporttab', attendances=attendances, **stats)

# -------------------------------
# Function for Admin ManageProfile Route
# -------------------------------
@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
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

