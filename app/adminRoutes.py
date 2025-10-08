# -------------------------------
# Standard library imports
# -------------------------------
import os
import re
import warnings
from io import BytesIO
from collections import defaultdict
from datetime import datetime, date
from zoneinfo import ZoneInfo
import random

# -------------------------------
# Third-party imports
# -------------------------------
import pandas as pd
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
import PyPDF2
from flask import render_template, request, redirect, url_for,flash, session, jsonify, send_file
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import func
from sqlalchemy import and_, or_

# -------------------------------
# Local application imports
# -------------------------------
from app import app
from .authRoutes import login_required, verifyAccount
from .backend import *
from .database import *

# -------------------------------
# Flask and application setup
# -------------------------------
# Initialize serializer and bcrypt
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

# Upload configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



# -------------------------------
# Function run non-stop
# -------------------------------
def cleanup_expired_timetable_rows():
    """Delete timetable rows whose classWeekDate end date has expired."""
    now = datetime.now()
    all_rows = TimetableRow.query.all()

    for row in all_rows:
        if not row.classWeekDate:
            continue

        start, end = parse_date_range(row.classWeekDate)
        if end is None:
            continue  # Skip malformed rows

        if now > end:
            db.session.delete(row)

    db.session.commit()  # Commit even if 0, or you can add a check


def update_attendanceStatus():
    all_attendance = InvigilatorAttendance.query.all()

    for attendance in all_attendance:
        report = attendance.report
        exam = report.exam if report else None

        if not exam:
            continue  # skip if exam is missing

        check_in = attendance.checkIn
        check_out = attendance.checkOut
        exam_start = exam.examStartTime
        exam_end = exam.examEndTime

        # Default remark
        remark = "PENDING"

        if check_in:
            if check_in <= exam_start - timedelta(hours=1):
                remark = "CHECK IN"
            elif check_in > exam_start:
                remark = "CHECK IN LATE"

        if check_out:
            if check_out < exam_end:
                remark = "CHECK OUT EARLY"
            elif check_out >= exam_end:
                remark = "CHECK OUT"

        attendance.remark = remark

    db.session.commit()













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
                        skiprows=1,      # skip the first row
                        header=0,        # take the next row as header
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
                        success, message = process_row_fn(row)
                        if success:
                            records_added += 1
                            flash(f'{message}',"success")
                        else:
                            records_failed += 1
                            flash(f'{message}',"error")

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
        department=str(row['department code']).strip(),
        code=str(row['course code']).strip().replace(" ", ""),
        section=str(row['course section']).strip().replace(" ", ""),
        name=str(row['course name']).strip(),
        hour=int(row['credit hour']),
        practical=str(row['practical lecturer']).strip().upper(),
        tutorial=str(row['tutorial lecturer']).strip().upper(),
        students=int(row['no of students']),
        status=True
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
        "courseCodeSection": course.courseCodeSectionIntake,
        "courseDepartment": course.courseDepartment,
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
                course_select.courseDepartment = request.form.get('departmentCode', '').strip()
                course_select.courseName = request.form.get('courseName', '').strip()
                course_select.coursePractical = request.form.get('practicalLecturerSelect', '').strip()
                course_select.courseTutorial = request.form.get('tutorialLecturerSelect', '').strip()
                course_select.courseStatus = True if request.form.get('courseStatus') == '1' else False

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
                            examVenue=None,
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
                "code": request.form.get('courseCode', '').replace(' ', ''),
                "section": request.form.get('courseSection', '').replace(' ', ''),
                "name": request.form.get('courseName', '').strip(),
                "hour": safe_int(request.form.get('courseHour')),
                "practical": request.form.get('practicalLecturerSelect', '').strip(),
                "tutorial": request.form.get('tutorialLecturerSelect', '').strip(),
                "students": safe_int(request.form.get('courseStudent')),
                "status": True
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
        "venueNumber": venue.venueNumber,
        "venueLevel": venue.venueLevel,
        "venueCapacity": venue.venueCapacity
    })

# -------------------------------
# Function for Admin ManageVenue Route
# -------------------------------
@app.route('/admin/manageVenue', methods=['GET', 'POST'])
@login_required
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
                    Exam.examEndTime.is_(None),
                    Exam.examVenue.is_(None)
                )
            )
        )
        .all()
    )
    for i, c in enumerate(courses, start=1):
        ws_lists[f"A{i}"] = c.courseCodeSectionIntake   # Course/Sec
        ws_lists[f"B{i}"] = c.courseDepartment          # Program
        ws_lists[f"C{i}"] = c.practicalLecturer.userName if c.practicalLecturer else ""  # Lecturer
        ws_lists[f"D{i}"] = c.courseStudent or 0        # No of students

    # --- Venues ---
    venues = Venue.query.all()
    for i, v in enumerate(venues, start=1):
        ws_lists[f"G{i}"] = v.venueNumber   # put venues in column G

    # === Data Validations ===
    if courses:
        dv_course = DataValidation(
            type="list",
            formula1=f"=Lists!$A$1:$A${len(courses)}",
            allow_blank=False
        )
        ws.add_data_validation(dv_course)
        dv_course.add("F3:F1002")  # Course/Sec dropdown

        # Auto-fill program, lecturers, no of students
        for row in range(3, 1003):
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
    conflict = VenueAvailability.query.filter(
        VenueAvailability.venueNumber == venue,
        VenueAvailability.startDateTime < end_dt + timedelta(minutes=30),
        VenueAvailability.endDateTime > start_dt - timedelta(minutes=30)
    ).first()

    if conflict:
        return None, ''

    # No conflict → create
    create_exam_and_related(start_dt, end_dt, str(row['course/sec']).upper(), venue, str(row['lecturer']).upper(), None, invigilatorNo=None)
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

    response_data = {
        "courseCodeSection": course.courseCodeSectionIntake,
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
    start_date = request.form.get('startDate')
    start_time = request.form.get('startTime')
    end_date = request.form.get('endDate')
    end_time = request.form.get('endTime')

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
        # Check for any conflict in VenueAvailability
        conflict = VenueAvailability.query.filter(
            VenueAvailability.venueNumber == venue.venueNumber,
            VenueAvailability.startDateTime < end_dt + timedelta(minutes=30),
            VenueAvailability.endDateTime > start_dt - timedelta(minutes=30),
        ).first()

        if not conflict:
            available_venues.append(venue.venueNumber)

    return jsonify({'venues': available_venues})

# -------------------------------
# Reassign invigilator for ManageExamEditPage
# -------------------------------
def adjust_invigilators(report, new_count, start_dt, end_dt):
    pending_hours = (end_dt - start_dt).total_seconds() / 3600.0
    current_attendances = list(report.attendances)
    current_count = len(current_attendances)

    if new_count == current_count:
        return  # nothing to change

    if new_count > current_count:
        extra_needed = new_count - current_count
        already_assigned_ids = [att.invigilatorId for att in current_attendances]

        eligible_invigilators = User.query.filter(
            User.userLevel == 1,
            User.userStatus == True,
            ~User.userId.in_(already_assigned_ids)
        ).all()

        if not eligible_invigilators:
            raise ValueError("No eligible invigilators available to add")

        # Split by gender
        male_invigilators = [inv for inv in eligible_invigilators if inv.userGender == "MALE"]
        female_invigilators = [inv for inv in eligible_invigilators if inv.userGender == "FEMALE"]

        # Sort by workload
        def workload(inv):
            return (inv.userCumulativeHours or 0) + (inv.userPendingCumulativeHours or 0)

        male_invigilators.sort(key=workload)
        female_invigilators.sort(key=workload)
        chosen_invigilators = []

        if new_count >= 2:
            # Ensure at least one male and one female if possible
            if male_invigilators:
                chosen_invigilators.append(male_invigilators.pop(0))
            if female_invigilators and len(chosen_invigilators) < extra_needed:
                chosen_invigilators.append(female_invigilators.pop(0))
            extra_needed -= len(chosen_invigilators)

        # Fill remaining slots with lowest workload invigilators
        pool = sorted(male_invigilators + female_invigilators, key=workload)
        chosen_invigilators += pool[:extra_needed]

        if len(chosen_invigilators) < new_count - current_count:
            raise ValueError("Not enough eligible invigilators to increase")

        # Assign chosen invigilators
        for inv in chosen_invigilators:
            inv.userPendingCumulativeHours = (inv.userPendingCumulativeHours or 0) + pending_hours
            db.session.add(InvigilatorAttendance(
                reportId=report.invigilationReportId,
                invigilatorId=inv.userId,
                timeCreate=datetime.now(timezone.utc)
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
@login_required
def admin_manageExam():
    # Automatically change exam status
    now = datetime.now()
    expired_exams = Exam.query.filter(Exam.examEndTime < now, Exam.examStatus == True).all()
    for exam in expired_exams:
        exam.examStatus = False
    db.session.commit()

    department_data = Department.query.all()

    # Base query: only exams whose course is active
    exam_data_query = Exam.query.join(Exam.course).filter(Course.courseStatus == True)
    exam_data = exam_data_query.order_by(Exam.examStatus.desc(),Exam.examStartTime.asc(),Exam.examVenue.asc(),Exam.examId.asc()).all()
    total_exam_activated = Exam.query.filter_by(examStatus=1).count()

    # For Edit section
    exam_selected = request.form.get('editExamCourseSection')
    course = Course.query.filter_by(courseCodeSectionIntake=exam_selected).first()
    exam_select = Exam.query.filter_by(examId=course.courseExamId).first() if course else None
    venue_data = Venue.query.order_by(Venue.venueCapacity.asc()).all()

    unassigned_exam = len([
        e for e in exam_data
        if e.examStatus is True
        and e.examStartTime is None
        and e.examEndTime is None
        and e.examVenue is None
    ])

    complete_exam = len([
        e for e in exam_data
        if e.examStatus is True
        and e.examStartTime is not None
        and e.examEndTime is not None
        and e.examVenue is not None
        and e.examNoInvigilator not in (None, 0)
    ])

    # Default manual form values
    venue_text = invigilatorNo_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # --------------------- UPLOAD ADD EXAM FORM ---------------------
        if form_type == 'upload':
            return handle_file_upload(
                file_key='exam_file',
                expected_cols=['date', 'day', 'start', 'end', 'program','course/sec','lecturer','no of','room'],
                process_row_fn=process_exam_row,
                redirect_endpoint='admin_manageExam',
                usecols="A:I",
                skiprows=1 
            )

        # --------------------- EDIT EXAM FORM ---------------------
        elif form_type == 'edit' and exam_select:
            action = request.form.get('action')
            start_date_raw = request.form.get('startDate', '').strip()
            start_time_raw = request.form.get('startTime', '').strip()
            end_date_raw = request.form.get('endDate', '').strip()
            end_time_raw = request.form.get('endTime', '').strip()
           
            start_dt = parse_datetime(start_date_raw, start_time_raw)
            end_dt = parse_datetime(end_date_raw, end_time_raw)
            venue_text = request.form.get('venue', '').strip()
            invigilatorNo_text = request.form.get('invigilatorNo', '0').strip()

            if action == 'update':
                venue_obj = Venue.query.filter_by(venueNumber=venue_text).first()

                if not venue_obj:
                    flash(f"Selected venue {venue_text} does not exist", "error")
                elif venue_obj.venueCapacity < exam_select.course.courseStudent:
                    flash(f"Venue capacity ({venue_obj.venueCapacity}) cannot fit {exam_select.course.courseStudent} student(s)", "error")
                else:
                    # Check for venue time conflict before saving
                    conflict = VenueAvailability.query.filter(
                        VenueAvailability.venueNumber == venue_text,
                        VenueAvailability.startDateTime < end_dt + timedelta(minutes=30),
                        VenueAvailability.endDateTime > start_dt - timedelta(minutes=30),
                        VenueAvailability.examId != exam_select.examId  # exclude same exam
                    ).first()

                    if conflict:
                        flash(f"Venue '{venue_text}' is already booked between "
                            f"{conflict.startDateTime.strftime('%Y-%m-%d %H:%M')} and "
                            f"{conflict.endDateTime.strftime('%Y-%m-%d %H:%M')}. "
                            f"Please choose a different time or venue.", "error")
                        return redirect(url_for('admin_manageExam'))

                    # Update exam core details
                    exam_select.examStartTime = start_dt
                    exam_select.examEndTime = end_dt
                    exam_select.examVenue = venue_text
                    exam_select.examNoInvigilator = invigilatorNo_text

                    # Ensure VenueAvailability is synced
                    existing_va = VenueAvailability.query.filter_by(examId=exam_select.examId).first()
                    if existing_va:
                        existing_va.venueNumber = venue_text
                        existing_va.startDateTime = start_dt
                        existing_va.endDateTime = end_dt
                    else:
                        new_va = VenueAvailability(
                            venueNumber=venue_text,
                            startDateTime=start_dt,
                            endDateTime=end_dt,
                            examId=exam_select.examId
                        )
                        db.session.add(new_va)

                    # Manage related InvigilationReport + Attendances
                    existing_report = InvigilationReport.query.filter_by(examId=exam_select.examId).first()

                    if not existing_report:
                        create_exam_and_related(start_dt, end_dt, exam_select.course.courseCodeSectionIntake, venue_text, exam_select.course.coursePractical, exam_select.course.courseTutorial, invigilatorNo_text)
                    elif exam_select.examNoInvigilator != int(invigilatorNo_text):
                        report = InvigilationReport.query.filter_by(examId=exam_select.examId).first()
                        if report:
                            adjust_invigilators(report, int(invigilatorNo_text), start_dt, end_dt)
                        else:
                            create_exam_and_related(start_dt, end_dt, exam_select.course.courseCodeSectionIntake, venue_text, exam_select.course.coursePractical, exam_select.course.courseTutorial, invigilatorNo_text)

                    db.session.commit()
                    flash("Exam updated successfully", "success")

            elif action == 'delete':
                reports = InvigilationReport.query.filter_by(examId=exam_select.examId).all()

                for report in reports:
                    attendances = InvigilatorAttendance.query.filter_by(reportId=report.invigilationReportId).all()

                    for attendance in attendances:
                        # Calculate duration to revert pending hours
                        if exam_select.examStartTime and exam_select.examEndTime:
                            duration = (exam_select.examEndTime - exam_select.examStartTime).total_seconds() / 3600.0
                            user = User.query.get(attendance.invigilatorId)
                            if user:
                                user.userPendingCumulativeHours -= duration
                                if user.userPendingCumulativeHours < 0:
                                    user.userPendingCumulativeHours = 0

                        # Delete attendance
                        db.session.delete(attendance)

                    # Delete invigilation report
                    db.session.delete(report)

                #  Delete venue availability
                venue_availabilities = VenueAvailability.query.filter_by(examId=exam_select.examId).all()
                for va in venue_availabilities:
                    db.session.delete(va)

                # Clear exam details (keep examId, examNoInvigilator)
                exam_select.examStartTime = None
                exam_select.examEndTime = None
                exam_select.examVenue = None

                db.session.commit()
                flash("Exam deleted successfully, and all related records were cleared.", "success")

            return redirect(url_for('admin_manageExam'))

    return render_template('admin/adminManageExam.html', active_tab='admin_manageExamtab', exam_data=exam_data, unassigned_exam=unassigned_exam, 
                           venue_data=venue_data, department_data=department_data, complete_exam=complete_exam, exam_select=exam_select, total_exam_activated=total_exam_activated)






















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
    headers = ['Id', 'Name', 'Department', 'Role', 'Email', 'Contact', 'Gender']
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
        dv_department.add("C3:C1002")  # Department dropdown

    dv_role = DataValidation(
        type="list",
        formula1=f"=Lists!$B$1:$B${len(roles)}",
        allow_blank=False
    )
    ws.add_data_validation(dv_role)
    dv_role.add("D3:D1002")  # Role dropdown

    dv_gender = DataValidation(
        type="list",
        formula1=f"=Lists!$C$1:$C${len(genders)}",
        allow_blank=False
    )
    ws.add_data_validation(dv_gender)
    dv_gender.add("G3:G1002")  # Gender dropdown

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
        "userStatus": str(user.userStatus)
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
                expected_cols=['id', 'name', 'department', 'role', 'email', 'contact', 'gender'],
                process_row_fn=process_staff_row,
                redirect_endpoint='admin_manageStaff',
                usecols="A:G",
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
    # Auto cleanup expired timetable rows
    # cleanup_expired_timetable_rows()

    department_data = Department.query.all()
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

    # Build mapping: user_id -> timetableId
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

        if form_type == 'upload':
            files = request.files.getlist("timetable_file[]")
            latest_files = {}
            skipped_files = []

            # ---- Compare & Keep only latest file for each lecturer ----
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

            # ---- Process each latest file ----
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

        elif form_type == 'manual':
            user_id = request.form.get("staffList")
            lecturer = request.form.get("lecturerName")

            if user_id and lecturer:
                # Ensure this user has a Timetable entry
                timetable = Timetable.query.filter_by(user_id=user_id).first()
                if not timetable:
                    timetable = Timetable(user_id=user_id)
                    db.session.add(timetable)
                    db.session.commit()

                # Update all rows for that lecturer
                rows = TimetableRow.query.filter_by(lecturerName=lecturer, timetable_id=None).all()
                for row in rows:
                    row.timetable_id = timetable.timetableId

                db.session.commit()
                flash(f"Timetable for {lecturer} has been successfully linked to Staff ID {user_id}.", "success")
            else:
                flash("Missing lecturer or staff", "error")

            return redirect(url_for('admin_manageTimetable'))

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

    return render_template('admin/adminManageTimetable.html', active_tab='admin_manageTimetabletab', timetable_data=timetable_data, lecturers=lecturers, selected_lecturer=selected_lecturer, unassigned_staff_list=unassigned_staff_list,
        total_timetable=total_timetable, unassigned_summary=unassigned_summary, staff_list=staff_list, **day_counts, timetable_list=timetable_list, timetable_map=timetable_map, timetable_select=timetable_select, department_data=department_data)













# -------------------------------
# Function for Admin ManageInviglationTimetable Route to read all the timetable in calendar mode
# -------------------------------
def get_calendar_data():
    attendances = get_all_attendances()
    calendar_data = defaultdict(list)
    seen_exams = set()
    all_exam_dates = []

    for att in attendances:
        exam = att.report.exam
        if exam.examId in seen_exams:
            continue
        seen_exams.add(exam.examId)

        start_time = exam.examStartTime
        end_time = exam.examEndTime

        # ✅ Detect if exam spans multiple days (overnight)
        is_overnight = start_time.date() != end_time.date()

        # ✅ Helper function to build exam dictionary
        def exam_dict(start, end):
            return {
                "start_time": start,
                "end_time": end,
                "exam_id": exam.examId,
                "course_name": exam.course.courseName,
                "course_code": exam.course.courseCodeSectionIntake,
                "venue": exam.examVenue,
                "status": exam.examStatus,
                "is_overnight": is_overnight  # ✅ Mark overnight exams
            }

        # ✅ Handle overnight exams (spanning across midnight)
        if is_overnight:
            # --- Part 1: from start to midnight ---
            calendar_data[start_time.date()].append(
                exam_dict(
                    start_time,
                    datetime.combine(start_time.date(), datetime.max.time()).replace(hour=23, minute=59)
                )
            )
            all_exam_dates.append(start_time.date())

            # --- Part 2: from midnight to real end ---
            calendar_data[end_time.date()].append(
                exam_dict(
                    datetime.combine(end_time.date(), datetime.min.time()),
                    end_time
                )
            )
            all_exam_dates.append(end_time.date())
        else:
            # ✅ Normal same-day exam
            calendar_data[start_time.date()].append(exam_dict(start_time, end_time))
            all_exam_dates.append(start_time.date())

    # ✅ Create full date range for the entire year
    if all_exam_dates:
        year = min(all_exam_dates).year
    else:
        year = datetime.now().year

    full_dates = []
    current = datetime(year, 1, 1).date()
    while current.year == year:
        full_dates.append(current)
        current += timedelta(days=1)

    return calendar_data, full_dates



# -------------------------------
# Function for Admin ManageInviglationTimetable Route
# -------------------------------
@app.route('/admin/manageInvigilationTimetable', methods=['GET', 'POST'])
@login_required
def admin_manageInvigilationTimetable():
    calendar_data, full_dates = get_calendar_data()
    return render_template('admin/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', calendar_data=calendar_data, full_dates=full_dates)








# -------------------------------
# Calculate All InvigilatorAttendance and InvigilationReport Data From Database
# -------------------------------
def calculate_invigilation_stats():
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
        .filter(Exam.examStatus == True)
        .all()
    )

    # Total active reports (InvigilationReport for exams with examStatus=True)
    total_report = (
        db.session.query(InvigilationReport)
        .join(Exam)  # joins on InvigilationReport.examId == Exam.examId via relationship
        .filter(Exam.examStatus == True)
        .count()
    )

    stats = {
        "total_report": total_report,
        "total_checkInOnTime": 0,
        "total_checkInLate": 0,
        "total_checkOutOnTime": 0,
        "total_checkOutEarly": 0,
        "total_checkInOut": 0,
        "total_inProgress": 0
    }

    for row in query:
        if row.checkIn is None:
            stats["total_checkInOut"] += 1
            continue

        if row.checkOut is None:
            stats["total_inProgress"] += 1
            continue

        if row.examStartTime and row.checkIn <= row.examStartTime:
            stats["total_checkInOnTime"] += 1
        elif row.examStartTime:
            stats["total_checkInLate"] += 1

        if row.examEndTime and row.checkOut >= row.examEndTime:
            stats["total_checkOutOnTime"] += 1
        elif row.examEndTime:
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
        .filter(InvigilatorAttendance.invigilationStatus == True)
        .order_by(Exam.examStatus.desc(), Exam.examStartTime.asc())
        .all()
    )

# -------------------------------
# Function for Admin ManageInviglationReport Route
# -------------------------------
@app.route('/admin/manageInvigilationReport', methods=['GET', 'POST'])
@login_required
def admin_manageInvigilationReport():
    update_attendanceStatus()
    attendances = get_all_attendances()

    # Add composite group key: (examStatus, examStartTime)
    for att in attendances:
        att.group_key = (not att.report.exam.examStatus, att.report.exam.examStartTime)

    stats = calculate_invigilation_stats()
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


