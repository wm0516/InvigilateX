from flask import render_template, request, redirect, url_for, flash, session, jsonify, Response
from app import app
from .backend import *
from .database import *
from datetime import  datetime, time
from io import BytesIO
import pandas as pd
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
import traceback
import os
import io
import json
from PyPDF2 import PdfReader
import re
import PyPDF2
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload


serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)





def get_all_attendances():
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .all()
    )


# function for admin manage invigilation timetable for all lecturer based on their availability (adding, editing, and removing)
@app.route('/admin/manageInvigilationTimetable', methods=['GET', 'POST'])
def admin_manageInvigilationTimetable():
    attendances = get_all_attendances()
    return render_template('admin/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', attendances=attendances)


# function for admin manage invigilation report for all lecturers after their inviiglation (adding, editing, and removing)
@app.route('/admin/manageInvigilationReport', methods=['GET', 'POST'])
def admin_manageInvigilationReport():
    attendances = get_all_attendances()
    return render_template('admin/adminManageInvigilationReport.html', active_tab='admin_manageInvigilationReporttab', attendances=attendances)


@app.route('/admin/manageDepartment', methods=['GET', 'POST'])
def admin_manageDepartment():
    department_data = Department.query.all()

    # Get all currently assigned dean and hop IDs
    assigned_dean_ids = db.session.query(Department.deanId).filter(Department.deanId.isnot(None)).distinct()
    assigned_hop_ids = db.session.query(Department.hopId).filter(Department.hopId.isnot(None)).distinct()
    
    # Default values for GET requests
    departmentCode = ''
    departmentName = ''
    deanId = ''
    hopId = ''

    # Exclude those already assigned
    dean_list = User.query.filter(User.userLevel == 2, ~User.userId.in_(assigned_dean_ids)).all()
    hop_list = User.query.filter(User.userLevel == 3, ~User.userId.in_(assigned_hop_ids)).all()

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

    return render_template('admin/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data, dean_list=dean_list, hop_list=hop_list)


# Can move those validation into a function then call again
@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    adminId = session.get('user_id')
    admin = User.query.filter_by(userId=adminId).first()

    # Default values for GET requests
    admin_contact_text = admin.userContact if admin else ''
    admin_password1_text = ''
    admin_password2_text = ''
    
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


@app.route('/admin/manageVenue', methods=['GET', 'POST'])
def admin_manageVenue():
    venue_data = Venue.query.all()

    # Default values for GET requests
    venueNumber_text = ''
    venueFloor_text = ''
    venueCapacity_text = ''
    venueStatus_text = ''

    if request.method == 'POST':
        venueNumber_text = request.form.get('venueNumber', '').strip().upper()
        venueFloor_text = request.form.get('venueFloor', '').strip()
        venueCapacity_text = request.form.get('venueCapacity', '').strip()
        venueStatus_text = request.form.get('venueStatus', '').strip()

        if Venue.query.filter_by(venueNumber=venueNumber_text).first():
            flash("Venue Room Already Exists", 'error')
        else:
            try:
                capacity = int(venueCapacity_text)
                if capacity < 0:
                    raise ValueError
                
                db.session.add(
                    Venue(
                        venueNumber=venueNumber_text,
                        venueFloor=venueFloor_text,
                        venueCapacity=capacity,
                        venueStatus=venueStatus_text
                    )
                )
                db.session.commit()
                flash("Venue Added", "success")
                return redirect(url_for('admin_manageVenue'))
            except ValueError:
                flash("Capacity must be a non-negative integer", 'error')

        return render_template('admin/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data, venueNumber_text=venueNumber_text, venueCapacity_text=venueCapacity_text)

    return render_template('admin/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data)




















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




# Main route
@app.route('/admin/manageCourse', methods=['GET', 'POST'])
def admin_manageCourse():
    course_data = Course.query.all()
    department_data = Department.query.all()

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

        # --------------------- UPLOAD FORM ---------------------
        if form_type == 'upload':
            file = request.files.get('course_file')
            if file and file.filename:
                try:
                    file_stream = BytesIO(file.read())
                    excel_file = pd.ExcelFile(file_stream)
                    course_records_added = 0

                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(
                                excel_file,
                                sheet_name=sheet_name,
                                usecols="A:H",
                                skiprows=1  
                            )

                            df.columns = [str(col).strip().lower() for col in df.columns]
                            expected_cols = ['department code', 'course code', 'course section', 'course name', 'credit hour', 'practical lecturer', 'tutorial lecturer', 'no of students']

                            if df.columns.tolist() != expected_cols:
                                raise ValueError("Excel columns do not match the expected format: " + str(df.columns.tolist()))

                            for col in df.columns:
                                df[col] = df[col].apply(lambda x: str(x).strip().lower() if isinstance(x, str) else x)

                            for index, row in df.iterrows():
                                try:
                                    courseDepartment_text = str(row['department code'])
                                    courseCode_text = str(row['course code'])
                                    courseSection_text = str(row['course section'])
                                    courseName_text = str(row['course name'])
                                    courseHour_text = row['credit hour']
                                    coursePractical_text = str(row['practical lecturer'])
                                    courseTutorial_text = str(row['tutorial lecturer'])
                                    courseStudent_text = row['no of students']

                                    valid, result = check_course(courseCode_text, courseSection_text, courseHour_text, courseStudent_text)
                                    if valid:
                                        create_course_and_exam(
                                            department=courseDepartment_text,
                                            code=courseCode_text,
                                            section=courseSection_text,
                                            name=courseName_text,
                                            hour=int(courseHour_text),
                                            practical=coursePractical_text,
                                            tutorial=courseTutorial_text,
                                            students=int(courseStudent_text)
                                        )
                                        course_records_added += 1
                                except Exception as row_err:
                                    print(f"[Row Error] {row_err}")
                        except Exception as sheet_err:
                            print(f"[Sheet Error] {sheet_err}")

                    if course_records_added > 0:
                        flash(f"Successful upload of {course_records_added} record(s)", 'success')
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

        # --------------------- DASHBOARD FORM ---------------------
        elif form_type == 'dashboard':
            return redirect(url_for('admin_manageCourse'))

        # --------------------- MANUAL ADD COURSE FORM ---------------------
        else:
            courseDepartment_text = request.form.get('departmentCode', '').strip()
            courseCode_text = request.form.get('courseCode', '').replace(' ', '')
            courseSection_text = request.form.get('courseSection', '').replace(' ', '')
            courseName_text = request.form.get('courseName', '').strip()
            courseHour_text = request.form.get('courseHour', '').strip()
            coursePractical_text = request.form.get('practicalLecturerSelect', '').strip()
            courseTutorial_text = request.form.get('tutorialLecturerSelect', '').strip()
            courseStudent_text = request.form.get('courseStudent', '').strip()

            valid, result = check_course(courseCode_text, courseSection_text, courseHour_text, courseStudent_text)
            if not valid:
                flash(result, 'error')
                return render_template('admin/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, department_data=department_data, 
                                       courseDepartment_text=courseDepartment_text, courseCode_text=courseCode_text, courseSection_text=courseSection_text,courseName_text=courseName_text, 
                                       courseHour_text=courseHour_text, coursePractical=coursePractical_text,courseTutorial=courseTutorial_text, courseStudent_text=courseStudent_text)

            # All valid, proceed to add course
            create_course_and_exam(
                department=courseDepartment_text,
                code=courseCode_text,
                section=courseSection_text,
                name=courseName_text,
                hour=int(courseHour_text),
                practical=coursePractical_text,
                tutorial=courseTutorial_text,
                students=int(courseStudent_text)
            )

            flash("New Course Added Successfully", "success")
            return redirect(url_for('admin_manageCourse'))

    # GET request fallback
    return render_template('admin/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, department_data=department_data)














































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

        if form_type == 'dashboard':
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






# Extract Base Name + Timestamp
def extract_base_name_and_timestamp(file_name):
    # Match base name + optional _DDMMYY
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
        # Remove ".pdf" and ignore trailing " extra text"
        base_name = re.sub(r"(_\d{6}.*)?\.pdf$", "", file_name, flags=re.IGNORECASE).strip()
        timestamp = None

    return base_name, timestamp



# Activity Parsing
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
            activity["weeks_date"] = weeks_data[-1]
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


# Parse Timetable
def parse_timetable(raw_text):
    text_no_whitespace = re.sub(r"\s+", "", raw_text)

    lecturer_name = None
    title_match = re.match(r"^(.*?)(07:00.*?23:00)", text_no_whitespace)
    if title_match:
        title_raw = title_match.group(1)
        timerow = title_match.group(2)
    else:
        title_raw = ""
        timerow = ""

    name_match = re.search(r"-([^-()]+)\(", title_raw)
    if name_match:
        raw_name = name_match.group(1)
        formatted_name = re.sub(r'(?<!^)([A-Z])', r' \1', raw_name).strip()
        formatted_name = formatted_name.replace("A/ P", "A/P").replace("A/ L", "A/L")
        lecturer_name = formatted_name
    else:
        lecturer_name = "UNKNOWN"

    if lecturer_name != "UNKNOWN":
        text_no_whitespace = text_no_whitespace.replace(raw_name, lecturer_name.replace(" ", ""))

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
        elif current_day and any(kw in line for kw in ["LECTURE", "TUTORIAL", "PRACTICAL"]):
            structured["days"][current_day].append(parse_activity(line))

    return structured


# Save to DB
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
                        "filename": filename,
                        "lecturerName": lecturer,
                        "classType": act.get("class_type"),
                        "classDay": day,
                        "classTime": act.get("time"),
                        "classRoom": act.get("room"),
                        "courseName": act.get("course"),
                        "courseIntake": sec.get("intake"),
                        "courseCode": sec.get("course_code"),
                        "courseSection": sec.get("section"),
                        "classWeekRange": ",".join(act.get("weeks_range", [])) if act.get("weeks_range") else None,
                        "classWeekDate": act.get("weeks_date"),
                    })

    # Bulk delete all rows for this lecturer before insert
    Timetable.query.filter_by(lecturerName=lecturer).delete()

    for entry in new_entries:
        row = Timetable(**entry)
        db.session.add(row)

    db.session.commit()
    return len(new_entries)



# Admin Route
@app.route('/admin/manageTimetable', methods=['GET', 'POST'])
def admin_manageTimetable():
    timetable_data = Timetable.query.order_by(Timetable.timetableId.asc()).all()
    lecturers = sorted({row.lecturerName for row in timetable_data})
    selected_lecturer = request.args.get("lecturer")

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

            timetable_data = Timetable.query.order_by(Timetable.timetableId.asc()).all()
            lecturers = sorted({row.lecturerName for row in timetable_data})

            return render_template(
                'admin/adminManageTimetable.html',
                active_tab='admin_manageTimetabletab',
                timetable_data=timetable_data,
                results=results,
                selected_lecturer=selected_lecturer_name,
                lecturers=lecturers,
                upload_summary={
                    "total_files_uploaded": total_files_read,
                    "files_uploaded": all_files,
                    "total_files_after_filter": total_files_filtered,
                    "files_after_filter": filtered_filenames,
                    "files_skipped": skipped_files
                }
            )

    return render_template(
        'admin/adminManageTimetable.html',
        active_tab='admin_manageTimetabletab',
        timetable_data=timetable_data,
        lecturers=lecturers,
        selected_lecturer=selected_lecturer
    )






