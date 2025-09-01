from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from .backend import *
from .database import *
from datetime import  datetime, time
from io import BytesIO
import pandas as pd
from flask_bcrypt import Bcrypt
from sqlalchemy import func
from itsdangerous import URLSafeTimedSerializer
import traceback
import os, json
import PyPDF2
import re


from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()


UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)





# function for admin manage invigilation timetable for all lecturer based on their availability (adding, editing, and removing)
@app.route('/admin/manageInvigilationTimetable', methods=['GET', 'POST'])
def admin_manageInvigilationTimetable():
    attendances = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .all()
    )
    return render_template('admin/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', attendances=attendances)



# function for admin manage invigilation report for all lecturers after their inviiglation (adding, editing, and removing)
@app.route('/admin/manageInvigilationReport', methods=['GET', 'POST'])
def admin_manageInvigilationReport():
    attendances = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .all()
    )
    return render_template('admin/adminManageInvigilationReport.html', active_tab='admin_manageInvigilationReporttab', attendances=attendances)


# function for admin to manage department information (adding, editing, and removing)
@app.route('/admin/manageDepartment', methods=['GET', 'POST'])
def admin_manageDepartment():
    department_data = Department.query.all()
    dean_list = User.query.filter(User.userLevel == 2).all()
    hop_list = User.query.filter(User.userLevel == 3).all()
    departmentCode_text = ''
    departmentName_text = ''
    deanName = ''
    hopName = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'announce':
            return redirect(url_for('admin_manageDepartment'))

        else:
            departmentCode_text = request.form.get('departmentCode', '').strip()
            departmentName_text = request.form.get('departmentName', '').strip()
            deanName = request.form.get('deanName', '').strip()
            hopName = request.form.get('hopName', '').strip()

            valid, result = check_department(departmentCode_text, departmentName_text)
            if not valid:
                flash(result, 'error')
                return render_template('admin/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data, 
                                       dean_list=dean_list, hop_list=hop_list, departmentCode_text=departmentCode_text, departmentName_text=departmentName_text)

            new_department = Department(
                departmentCode=departmentCode_text.upper(),
                departmentName=departmentName_text.upper(),
                deanId=deanName.upper() if deanName else None,
                hopId=hopName.upper() if hopName else None
            )
            db.session.add(new_department)
            db.session.commit()
            flash("New Department Added Successfully", "success")
            return redirect(url_for('admin_manageDepartment'))

    return render_template('admin/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data, dean_list=dean_list, hop_list=hop_list)


# function for admin to manage venue information (adding, editing, and removing)
@app.route('/admin/manageVenue', methods=['GET', 'POST'])
def admin_manageVenue():
    venue_data = Venue.query.all()
    venueNumber_text = ''
    venueFloor_text = ''
    venueCapacity_text = ''
    venueStatus_text = ''

    if request.method == 'POST':
        venueNumber_text = request.form.get('venueNumber', '').strip()
        venueFloor_text = request.form.get('venueFloor', '').strip()
        venueCapacity_text = request.form.get('venueCapacity', '').strip()
        venueStatus_text = request.form.get('venueStatus', '').strip()

        valid, result = check_venue(venueNumber_text, venueCapacity_text)
        if not valid:
            flash(result, 'error')
            return render_template('admin/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data, venueNumber_text=venueNumber_text, venueCapacity_text=venueCapacity_text)

        new_venue = Venue(
            venueNumber=venueNumber_text.upper(),
            venueFloor=venueFloor_text.upper(),
            venueCapacity=venueCapacity_text,
            venueStatus=venueStatus_text.upper()
        )
        db.session.add(new_venue)
        db.session.commit()
        flash("New Venue Added Successfully", "success")
        return redirect(url_for('admin_manageVenue'))

    return render_template('admin/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data)


# Can move those validation into a function then call again
@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    adminId = session.get('user_id')
    admin = User.query.filter_by(userId=adminId).first()
    
    # Pre-fill existing data
    admin_password1_text = ''
    admin_password2_text = ''
    error_message = None

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

    return render_template(
        'admin/adminProfile.html',
        active_tab='admin_profiletab',
        admin_name=admin.userName if admin else '',
        admin_id=admin.userId if admin else '',
        admin_email=admin.userEmail if admin else '',
        admin_department_text=admin.userDepartment if admin else '',
        admin_gender=admin.userGender if admin else '',
        admin_role_text={
            LECTURER: "LECTURER",
            HOP: "HOP",
            DEAN: "DEAN",
            ADMIN: "ADMIN"
        }.get(admin.userLevel, "Unknown") if admin else '',
        admin_contact_text=admin.userContact if admin else '',
        admin_password1_text=admin_password1_text,
        admin_password2_text=admin_password2_text,
        error_message=error_message
    )


# function for handle date from excel file and read it
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










# Function for admin to manage lecturer, dean, and hop information (adding, editing, and removing)
@app.route('/admin/manageStaff', methods=['GET', 'POST'])
def admin_manageStaff():
    user_data = User.query.all()
    department_data = Department.query.all()

    # Default form field values
    id_text = ''
    name_text = ''
    email_text = ''
    contact_text = ''
    gender_text = ''
    department_text = ''
    role_text = ''
    error_message = None

    role_map = {
        'LECTURER': LECTURER,
        'DEAN': DEAN,
        'HOP': HOP,
        'ADMIN': ADMIN
    }

    if request.method == 'POST':
        form_type = request.form.get('form_type')  # <-- Distinguish which form was submitted

        if form_type == 'upload':
            file = request.files.get('staff_file')
            if file and file.filename:
                try:
                    file_stream = BytesIO(file.read())
                    excel_file = pd.ExcelFile(file_stream)
                    print(f"Found sheets: {excel_file.sheet_names}")

                    staff_records_added = 0

                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(
                                excel_file,
                                sheet_name=sheet_name,
                                usecols="A:G",
                                skiprows=1
                            )

                            print(f"Raw columns from sheet '{sheet_name}': {df.columns.tolist()}")
                            df.columns = [str(col).strip().lower() for col in df.columns]
                            expected_cols = ['id', 'name', 'department', 'role', 'email', 'contact', 'gender']

                            if df.columns.tolist() != expected_cols:
                                raise ValueError("Excel columns do not match the expected format: " + str(df.columns.tolist()))

                            #  Normalize all string values to lowercase
                            for col in df.columns:
                                df[col] = df[col].apply(lambda x: str(x).strip().lower() if isinstance(x, str) else x)

                            role_mapping = {
                                'lecturer': 1,
                                'hop': 2,
                                'dean': 3,
                                'admin': 4
                            }

                            for index, row in df.iterrows():
                                try:
                                    id_text = str(row['id']).upper()
                                    name_text = str(row['name']).upper()
                                    department_text = str(row['department']).upper()
                                    email_text = str(row['email'])
                                    contact_text = str(row['contact'])
                                    gender_text = str(row['gender']).upper()
                                    role_text_str = str(row['role']).strip().lower()
                                    role_text = role_mapping.get(role_text_str)
                                    hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')

                                    valid, result = check_staff(id_text, email_text, contact_text)
                                    if valid:
                                        new_staff = User(
                                            userId=id_text,
                                            userDepartment=department_text,
                                            userName=name_text,
                                            userLevel=role_text,
                                            userEmail=email_text,
                                            userContact=contact_text,
                                            userGender=gender_text,
                                            userPassword=hashed_pw
                                        )
                                        db.session.add(new_staff)
                                        db.session.commit()
                                        staff_records_added += 1
                                except Exception as row_err:
                                    print(f"[Row Error] {row_err}")
                        except Exception as sheet_err:
                            print(f"[Sheet Error] {sheet_err}")

                    if staff_records_added > 0:
                        flash(f"Successful upload {staff_records_added} record(s)", 'success')
                    else:
                        flash("No data uploaded", 'error')

                    return redirect(url_for('admin_manageStaff'))

                except Exception as e:
                    print(f"[File Processing Error] {e}")
                    flash('File processing error: File upload in wrong format', 'error')
                    return redirect(url_for('admin_manageStaff'))
            else:
                flash("No file uploaded", 'error')
                return redirect(url_for('admin_manageStaff'))

        elif form_type == 'modify':
            return redirect(url_for('admin_manageStaff'))
        
        elif form_type == 'manual':
            id_text = request.form.get('userid', '').strip()
            name_text = request.form.get('username', '').strip()
            email_text = request.form.get('email', '').strip()
            contact_text = request.form.get('contact', '').strip()
            gender_text = request.form.get('gender', '').strip()
            department_text = request.form.get('department', '').strip()
            role_text = request.form.get('role', '').strip()
            hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')

            valid, result = check_staff(id_text, email_text, contact_text)
            if not valid:
                flash(result, 'error')
                return render_template(
                    'admin/adminManageStaff.html',
                    user_data=user_data,
                    department_data=department_data,
                    id_text=id_text,
                    name_text=name_text,
                    email_text=email_text,
                    contact_text=contact_text,
                    department_text=department_text,
                    role_text=role_text,gender_text=gender_text,
                    active_tab='admin_manageStafftab'
                )

            new_staff = User(
                userId=id_text.upper(),
                userDepartment=department_text.upper(),
                userName=name_text.upper(),
                userLevel=role_map[role_text],
                userEmail=email_text,
                userContact=contact_text,
                userGender=gender_text,
                userPassword=hashed_pw
            )
            db.session.add(new_staff)
            db.session.commit()
            flash("New Staff Added Successfully", "success")
            return redirect(url_for('admin_manageStaff'))

    return render_template('admin/adminManageStaff.html', active_tab='admin_manageStafftab', user_data=user_data, department_data=department_data)


# Function for admin to manage course information (adding, editing, and removing)
@app.route('/admin/manageCourse', methods=['GET', 'POST'])
def admin_manageCourse():
    course_data = Course.query.all()
    department_data = Department.query.all()
    lecturer_data = User.query.filter(User.userLevel == 1).all()

    # Default form field values
    courseDepartment_text = ''
    courseCode_text = ''
    courseSection_text = ''
    courseName_text = ''
    courseHour_text = ''
    coursePractical_text = ''
    courseTutorial_text = ''
    courseStudent_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')  # <-- Distinguish which form was submitted

        if form_type == 'upload':
            file = request.files.get('course_file')
            print(f"Found: {file}")
            if file and file.filename:
                try:
                    file_stream = BytesIO(file.read())
                    excel_file = pd.ExcelFile(file_stream)
                    print(f"Found sheets: {excel_file.sheet_names}")

                    course_records_added = 0

                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(
                                excel_file,
                                sheet_name=sheet_name,
                                usecols="A:H",
                                skiprows=1  
                            )

                            print(f"Raw columns from sheet '{sheet_name}': {df.columns.tolist()}")
                            df.columns = [str(col).strip().lower() for col in df.columns]
                            expected_cols = ['department code', 'course code', 'course section', 'course name', 'credit hour', 'practical lecturer', 'tutorial lecturer', 'no of students']

                            if df.columns.tolist() != expected_cols:
                                raise ValueError("Excel columns do not match the expected format: " + str(df.columns.tolist()))

                            #  Normalize all string values to lowercase
                            for col in df.columns:
                                df[col] = df[col].apply(lambda x: str(x).strip().lower() if isinstance(x, str) else x)

                            for index, row in df.iterrows():
                                try:
                                    courseDepartment_text = str(row['department code'])
                                    department_text = courseDepartment_text.split('-')[0].strip()
                                    courseCode_text = str(row['course code'])
                                    courseSection_text = str(row['course section'])
                                    courseName_text = str(row['course name'])
                                    courseHour_text = int(row['credit hour'])
                                    coursePractical_text = str(row['practical lecturer'])
                                    courseTutorial_text = str(row['tutorial lecturer'])
                                    courseStudent_text = str(row['no of students'])
                                    courseCodeSection_text = courseCode_text + '/' + courseSection_text

                                    valid, result = check_course(courseCode_text, courseSection_text, courseHour_text, courseStudent_text)
                                    if valid:
                                        # 1. Create Exam
                                        new_exam = Exam(
                                            examVenue=None,
                                            examStartTime=None,
                                            examEndTime=None,
                                            examNoInvigilator=None,
                                        )
                                        db.session.add(new_exam)
                                        db.session.flush()  # ensures examId is generated

                                        # 2. Create and add the course
                                        new_course = Course(
                                            courseDepartment=department_text.upper(),
                                            courseCodeSection=courseCodeSection_text.upper(),
                                            courseCode=courseCode_text.upper(),
                                            courseSection=courseSection_text.upper(),
                                            courseName=courseName_text.upper(),
                                            courseHour=courseHour_text,
                                            coursePractical=coursePractical_text.upper(),
                                            courseTutorial=courseTutorial_text.upper(),
                                            courseStudent=courseStudent_text,
                                            courseExamId=new_exam.examId
                                        )
                                        db.session.add(new_course)
                                        db.session.flush()  # makes new_course available in session

                                        # 3. Commit everything
                                        db.session.commit()
                                        course_records_added += 1
                                except Exception as row_err:
                                    print(f"[Row Error] {row_err}")
                        except Exception as sheet_err:
                            print(f"[Sheet Error] {sheet_err}")

                    if course_records_added > 0:
                        flash(f"Successful upload {course_records_added} record(s)", 'success')
                    else:
                        flash("No data uploaded", 'error')

                    return redirect(url_for('admin_manageCourse'))

                except Exception as e:
                    print(f"[File Processing Error] {e}")
                    flash('File processing error: File upload in wrong format', 'error')
                    return redirect(url_for('admin_manageCourse'))
            else:
                flash("No file uploaded", 'error')
                return redirect(url_for('admin_manageCourse'))
        

        elif form_type == 'announce':
            return redirect(url_for('admin_manageCourse'))

        else:
            courseDepartment_text = request.form.get('departmentCode', '').strip()
            department_text = courseDepartment_text.split('-')[0].strip()
            courseCode_text = request.form.get('courseCode', '').replace(' ', '')
            courseSection_text = request.form.get('courseSection', '').replace(' ', '')
            courseName_text = request.form.get('courseName', '').strip()
            courseHour_text = request.form.get('courseHour', '').strip()
            coursePractical_text = request.form.get('practicalLecturerSelect', '').strip()
            courseTutorial_text = request.form.get('tutorialLecturerSelect', '').strip()
            courseStudent_text = request.form.get('courseStudent', '').strip()
            courseCodeSection_text = courseCode_text + '/' + courseSection_text

            valid, result = check_course(courseCode_text, courseSection_text, courseHour_text, courseStudent_text)
            if not valid:
                flash(result, 'error')
                return render_template('admin/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, department_data=department_data, lecturer_data=lecturer_data,
                                       courseDepartment_text=courseDepartment_text, courseCode_text=courseCode_text, courseSection_text=courseSection_text, courseName_text=courseName_text, 
                                       courseHour_text=courseHour_text, coursePractical=coursePractical_text, courseTutorial=courseTutorial_text, courseStudent_text=courseStudent_text)

            if valid:
                # 1. Create Exam
                new_exam = Exam(
                    examVenue=None,
                    examStartTime=None,
                    examEndTime=None,
                    examNoInvigilator=None,
                )
                db.session.add(new_exam)
                db.session.flush()  # ensures examId is generated

                # 2. Create and add the course
                new_course = Course(
                    courseDepartment=department_text.upper(),
                    courseCodeSection=courseCodeSection_text.upper(),
                    courseCode=courseCode_text.upper(),
                    courseSection=courseSection_text.upper(),
                    courseName=courseName_text.upper(),
                    courseHour=courseHour_text,
                    coursePractical=coursePractical_text.upper(),
                    courseTutorial=courseTutorial_text.upper(),
                    courseStudent=courseStudent_text,
                    courseExamId=new_exam.examId
                )
                db.session.add(new_course)
                db.session.flush()  # makes new_course available in session

                # 3. Commit everything
                db.session.commit()
            flash("New Course Added Successfully", "success")
            return redirect(url_for('admin_manageCourse'))
            
    return render_template('admin/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, department_data=department_data, lecturer_data=lecturer_data)


# Function for admin to manage exam information (adding, editing, and removing)
@app.route('/admin/manageExam', methods=['GET', 'POST'])
def admin_manageExam():
    department_data = Department.query.all() # For department code dropdown
    venue_data = Venue.query.filter(Venue.venueStatus == 'AVAILABLE').all() # For venue selection dropdown
    exam_data = Exam.query.filter(Exam.examStartTime.isnot(None), Exam.examEndTime.isnot(None)).all()   # Display out only with value data, null value data will not be displayed out 
    course_data = Course.query.join(Exam).filter(Exam.examStartTime.is_(None), Exam.examEndTime.is_(None)).all()
 
    # Default values for manual form
    courseSection_text = ''
    practicalLecturer_text = ''
    tutorialLecturer_text = ''
    venue_text = ''
    invigilatorNo_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ===== File Upload =====
        '''
        if form_type == 'upload':
            file = request.files.get('exam_file')
            print(f"Read file: {file}")
            if file and file.filename:
                try:
                    file_stream = BytesIO(file.read())
                    excel_file = pd.ExcelFile(file_stream)

                    abbr_to_full = {day[:3].lower(): day for day in calendar.day_name}
                    exam_records_added = 0
                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(
                                excel_file,
                                sheet_name=sheet_name,
                                usecols="A:I",
                                skiprows=1
                            )
                            df.columns = [str(col).strip().lower() for col in df.columns]
                            expected_cols = ['date', 'day', 'start', 'end', 'program', 'course/sec', 'lecturer', 'no of', 'room']
                            print(f"Read file table: {expected_cols}")

                            if df.columns.tolist() != expected_cols:
                                raise ValueError("Excel columns do not match expected format")
                            
                            # Normalize all string columns except 'day' to lowercase
                            for col in df.columns:
                                if col != 'day':
                                    df[col] = df[col].apply(lambda x: str(x).strip().lower() if isinstance(x, str) else x)

                            # Convert 'day' abbreviations to full day names
                            df['day'] = df['day'].apply(
                                lambda x: abbr_to_full.get(str(x).strip()[:3].lower(), x) if isinstance(x, str) else x
                            )

                            for index, row in df.iterrows():
                                try:
                                    # Parse the date, time, and other data
                                    examDate_text = parse_date(row['date'])  # Parsed date from Excel
                                    startTime_text = standardize_time_with_seconds(row['start'])  # Parsed time from Excel
                                    endTime_text = standardize_time_with_seconds(row['end'])  # Parsed time from Excel

                                    if not examDate_text:
                                        raise ValueError(f"Invalid date at row {index}")

                                    if not startTime_text or not endTime_text:
                                        raise ValueError(f"Invalid time at row {index}")

                                    # Convert date and time into datetime
                                    start_dt = datetime.combine(examDate_text, datetime.strptime(startTime_text, "%H:%M:%S").time())
                                    end_dt = datetime.combine(examDate_text, datetime.strptime(endTime_text, "%H:%M:%S").time())

                                    # Additional data parsing
                                    courseSection_text = str(row['course/sec']).upper()
                                    practicalLecturer_text = tutorialLecturer_text = str(row['lecturer']).upper()
                                    venue_text = str(row['room']).upper()
                                    invigilatorNo_text = row['no of invigilator']

                                    # Now proceed with your existing logic, e.g., create the exam and save it
                                    create_exam_and_related(examDate_text, start_dt, end_dt, courseSection_text, venue_text, practicalLecturer_text, tutorialLecturer_text, invigilatorNo_text)
                                    db.session.commit()
                                    exam_records_added += 1

                                except Exception as row_err:
                                    print(f"[Row Error] {row_err}")
                        except Exception as sheet_err:
                            print(f"[Sheet Error] {sheet_err}")

                    flash(f"Successfully uploaded {exam_records_added} record(s)" if exam_records_added > 0 else "No data uploaded", 
                          'success' if exam_records_added > 0 else 'error')
                    return redirect(url_for('admin_manageExam'))

                except Exception as e:
                    print(f"[File Processing Error] {e}")
                    flash('File processing error: File upload in wrong format', 'error')
                    return redirect(url_for('admin_manageExam'))
            else:
                flash("No file uploaded", 'error')
                return redirect(url_for('admin_manageExam'))
        '''

        if form_type == 'announce':
            return redirect(url_for('admin_manageExam'))

        # ===== Manual Add =====
        elif form_type == 'manual':
            try:
                # --- Raw input ---
                startDate_raw = request.form.get('startDate', '').strip()
                endDate_raw = request.form.get('endDate', '').strip()
                startTime_raw = request.form.get('startTime', '').strip()
                endTime_raw = request.form.get('endTime', '').strip()

                # --- Normalize time strings ---
                if len(startTime_raw) == 5:   # HH:MM → add :00
                    startTime_raw += ":00"
                if len(endTime_raw) == 5:
                    endTime_raw += ":00"

                # --- Convert to datetime objects ---
                start_dt = datetime.strptime(f"{startDate_raw} {startTime_raw}", "%Y-%m-%d %H:%M:%S")
                end_dt   = datetime.strptime(f"{endDate_raw} {endTime_raw}", "%Y-%m-%d %H:%M:%S")

                # --- Other fields ---
                courseSection_text = request.form.get('courseSection', '').strip()
                venue_text = request.form.get('venue', '').strip()
                practicalLecturer_text = request.form.get('practicalLecturer', '').strip()
                tutorialLecturer_text = request.form.get('tutorialLecturer', '').strip()
                invigilatorNo_text = int(request.form.get('invigilatorNo', '0'))

                # --- Call core function ---
                create_exam_and_related(start_dt, end_dt, courseSection_text, venue_text, practicalLecturer_text, tutorialLecturer_text, invigilatorNo_text)
                flash("New Exam Record Added Successfully", "success")
                return redirect(url_for('admin_manageExam'))

            except Exception as manual_err:
                print(f"[Manual Form Error] {manual_err}")
                traceback.print_exc()
                flash(f"Error processing manual form: {manual_err}", 'error')
                return redirect(url_for('admin_manageExam'))

    return render_template('admin/adminManageExam.html', active_tab='admin_manageExamtab', exam_data=exam_data, course_data=course_data, venue_data=venue_data, department_data=department_data)


# ===== to get the all lecturers only that under the department search for the manage course page =====
@app.route('/get_lecturers_by_department/<department_code>')
def get_lecturers_by_department(department_code):
    # Ensure case-insensitive match if needed
    print(f"User Department Code is: {department_code}")
    lecturers = User.query.filter_by(userDepartment=department_code, userLevel=1).all()
    lecturers_list = [{"userId": l.userId, "userName": l.userName} for l in lecturers]
    return jsonify(lecturers_list)


# ===== to get all course that under the department for the manage exam page ====
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



# ===== to get all course details that under the department for the manage exam page ====
@app.route('/get_course_details/<program_code>/<path:course_code_section>')  # ✅ FIXED HERE
def get_course_details(program_code, course_code_section):
    print(f"Requested: program_code={program_code}, course_code_section={course_code_section}")  # Optional debug
    selected_course = Course.query.filter_by(
        courseDepartment=program_code,
        courseCodeSection=course_code_section
    ).first()
    if selected_course:
        return jsonify({
            "practicalLecturer": selected_course.coursePractical,
            "tutorialLecturer": selected_course.courseTutorial,
            "student": selected_course.courseStudent
        })
    return jsonify({"error": "Course not found"})








from googleapiclient.discovery import build
from google.oauth2 import service_account

# Path to your downloaded JSON key
SERVICE_ACCOUNT_FILE = '/home/WM05/mydriveapiproject-470807-b5aaec17be0f.json'  # update path
SCOPES = ['https://www.googleapis.com/auth/drive']

# Create credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Build the Drive API service
service = build('drive', 'v3', credentials=credentials)

# List first 10 files in shared Drive
results = service.files().list(pageSize=10).execute()
items = results.get('files', [])

if not items:
    print('No files found.')
else:
    for item in items:
        print(f"{item['name']} ({item['id']})")











'''
def get_drive_service():
    SERVICE_ACCOUNT_FILE = '/home/WM05/credentials.json'
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def find_folder_id(service, folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if not folders:
        print(f"Folder '{folder_name}' not found.")
        return None
    # If multiple folders named "SOC" exist, pick the first
    return folders[0]['id']

def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    return files

@app.route("/admin/manageTimetable", methods=["GET"])
def admin_manageTimetable():
    service = get_drive_service()
    
    folder_name = 'SOC'
    folder_id = find_folder_id(service, folder_name)
    
    if folder_id:
        files = list_files_in_folder(service, folder_id)
        print(f"Files in folder '{folder_name}':")
        for file in files:
            print(f" - {file['name']} (ID: {file['id']}, Type: {file['mimeType']})")

    return render_template("admin/adminManageTimetable.html", active_tab="admin_manageTimetabletab")
'''







def parse_activity(line):
    """Parse one activity line into structured data."""
    activity = {}

    # Class type (LECTURE/TUTORIAL/PRACTICAL)
    m_type = re.match(r"(LECTURE|TUTORIAL|PRACTICAL)", line)
    if m_type:
        activity["class_type"] = m_type.group(1)

    # Time
    m_time = re.search(r",(\d{2}:\d{2}-\d{2}:\d{2})", line)
    if m_time:
        activity["time"] = m_time.group(1)

    # Weeks and date range
    m_weeks = re.search(r"WEEKS:([^C]+)", line)
    if m_weeks:
        weeks_data = m_weeks.group(1).split(",")
        if len(weeks_data) > 1:
            activity["weeks_range"] = weeks_data[:-1]
            activity["weeks_date"] = weeks_data[-1]
        else:
            activity["weeks_range"] = weeks_data

    # Course name
    m_course = re.search(r"COURSES:([^;]+);", line)
    if m_course:
        activity["course"] = m_course.group(1)

    # Sections
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

    # Room
    m_room = re.search(r"ROOMS:([^;]+);", line)
    if m_room:
        activity["room"] = m_room.group(1)

    return activity




'''
@app.route("/admin/manageTimetable", methods=["GET", "POST"])
def admin_manageTimetable():
    service = get_drive_service()
    results = service.files().list(pageSize=50, fields="files(id, name)").execute()
    files = results.get('files', [])
    for file in files:
        print(f"{file['name']} ({file['id']})")


    structured = None

    if request.method == "POST":
        if "timetablePDF_file" not in request.files:
            flash("No file part", "error")
            return redirect(request.url)

        file = request.files["timetablePDF_file"]

        if file.filename == "":
            flash("No selected file", "error")
            return redirect(request.url)

        reader = PyPDF2.PdfReader(file.stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + " "

        # Remove ALL whitespace
        text = re.sub(r"\s+", "", text)
        text = text.upper()

        # --- Step 1: Extract title ---
        match_title = re.match(r"^(.*?)(07:00.*?23:00)", text)
        if match_title:
            title = match_title.group(1).strip()
            timerow = match_title.group(2).strip()
            text = text.replace(title, "").replace(timerow, "")
        else:
            title = "TIMETABLE"
            timerow = ""

        # --- Extract lecturer name ---
        lecturer_name = None
        match_name = re.search(r"-(.*?)\(", title)
        if match_name:
            lecturer_name = match_name.group(1)

        # --- Step 2: Insert days with blank line before them ---
        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        for day in days:
            text = re.sub(day, f"\n\n{day}", text, flags=re.IGNORECASE)

        # --- Step 3: Break activities so each starts on new line ---
        keywords = ["LECTURE", "TUTORIAL", "PRACTICAL", "PUBLISHED"]
        for kw in keywords:
            if kw == "PUBLISHED":
                text = re.sub(kw, f"\n\n{kw}", text, flags=re.IGNORECASE)
            else:
                text = re.sub(kw, f"\n{kw}", text, flags=re.IGNORECASE)

        # --- Step 4: Clean up ---
        text = re.sub(r"\n{3,}", "\n\n", text)

        # --- Step 5: Build structured JSON ---
        structured = {
            "title": title,
            "lecturer": lecturer_name,
            "timerow": timerow,
            "days": {}
        }
        current_day = None

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if line in days:
                current_day = line
                structured["days"][current_day] = []
            else:
                if current_day and any(kw in line for kw in ["LECTURE", "TUTORIAL", "PRACTICAL"]):
                    structured["days"][current_day].append(parse_activity(line))

    return render_template("admin/adminManageTimetable.html", active_tab="admin_manageTimetabletab", structured=structured)
'''









