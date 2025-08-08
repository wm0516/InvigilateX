from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from .backend import *
from .database import *
from datetime import  datetime
import os
from io import BytesIO
import pandas as pd
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




# function for admin manage invigilation report for all lecturers after their inviiglation (adding, editing, and removing)
@app.route('/adminHome/manageInvigilationReport', methods=['GET', 'POST'])
def admin_manageInvigilationReport():
    return render_template('adminPart/adminManageInvigilationReport.html', active_tab='admin_manageInvigilationReporttab')



# function for admin manage lecturer timetable (adding, editing, and removing)
@app.route('/adminHome/manageTimetable', methods=['GET', 'POST'])
def admin_manageTimetable():
    user_data = User.query.all()
    return render_template('adminPart/adminManageTimetable.html', active_tab='admin_manageTimetabletab', user_data=user_data)





# function for admin manage invigilation timetable for all lecturer based on their availability (adding, editing, and removing)
@app.route('/adminhome/manageInvigilationTimetable', methods=['GET', 'POST'])
def admin_manageInvigilationTimetable():
    exam_data = Exam.query.all()
    user_data = User.query.all()
    department_data = Department.query.all()

    return render_template('adminPart/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', 
                           user_data=user_data, exam_data=exam_data, department_data=department_data)


# function for admin to manage department information (adding, editing, and removing)
@app.route('/adminHome/manageDepartment', methods=['GET', 'POST'])
def admin_manageDepartment():
    department_data = Department.query.all()
    departmentCode_text = ''
    departmentName_text = ''

    if request.method == 'POST':
        departmentCode_text = request.form.get('departmentCode', '').strip()
        departmentName_text = request.form.get('departmentName', '').strip()

        valid, result = check_department(departmentCode_text, departmentName_text)
        if not valid:
            flash(result, 'error')
            return render_template('adminPart/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', 
                                   department_data=department_data, departmentCode_text=departmentCode_text, departmentName_text=departmentName_text)

        new_department = Department(
            departmentCode=departmentCode_text.upper(),
            departmentName=departmentName_text.upper()
        )
        db.session.add(new_department)
        db.session.commit()
        flash("New Department Added Successfully", "success")
        return redirect(url_for('admin_manageDepartment'))

    return render_template('adminPart/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data)



# function for admin to manage venue information (adding, editing, and removing)
@app.route('/adminHome/manageVenue', methods=['GET', 'POST'])
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
            return render_template('adminPart/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data, venueNumber_text=venueNumber_text, 
                                   venueFloor_text=venueFloor_text, venueCapacity_text=venueCapacity_text, venueStatus_text=venueStatus_text)

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

    return render_template('adminPart/adminManageVenue.html', active_tab='admin_manageVenuetab', venue_data=venue_data)



































# Can move those validation into a function then call again
@app.route('/adminHome/profile', methods=['GET', 'POST'])
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
        'adminPart/adminProfile.html',
        active_tab='admin_profiletab',
        admin_name=admin.userName if admin else '',
        admin_id=admin.userId if admin else '',
        admin_email=admin.userEmail if admin else '',
        admin_department_text=admin.userDepartment if admin else '',
        admin_gender=admin.userGender if admin else '',
        admin_role_text={
            LECTURER: "Lecturer",
            HOP: "Hop",
            DEAN: "Dean",
            ADMIN: "Admin"
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


# function for admin to manage lecturer, dean, and hop information (adding, editing, and removing)
@app.route('/adminHome/manageLecturer', methods=['GET', 'POST'])
def admin_manageLecturer():
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
            file = request.files.get('lecturer_file')
            if file and file.filename:
                try:
                    file_stream = BytesIO(file.read())
                    excel_file = pd.ExcelFile(file_stream)
                    print(f"Found sheets: {excel_file.sheet_names}")

                    lecturer_records_added = 0

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

                            df.columns = ['id', 'name', 'department', 'role', 'email', 'contact', 'gender']

                            role_mapping = {
                                'lecturer': 1,
                                'hop': 2,
                                'dean': 3,
                                'admin': 4
                            }

                            for index, row in df.iterrows():
                                try:
                                    id_text = str(row['id'])
                                    name_text = str(row['name']).upper()
                                    department_text = str(row['department']).upper()
                                    email_text = str(row['email'])
                                    contact_text = str(row['contact'])
                                    gender_text = str(row['gender']).upper()
                                    role_text_str = str(row['role']).strip().lower()
                                    role_text = role_mapping.get(role_text_str)
                                    hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')

                                    valid, result = check_lecturer(id_text, email_text, contact_text)
                                    if valid:
                                        new_lecturer = User(
                                            userId=id_text,
                                            userName=name_text,
                                            userDepartment=department_text,
                                            userGender=gender_text,
                                            userLevel=role_text,
                                            userEmail=email_text,
                                            userContact=contact_text,
                                            userStatus=False,
                                            userPassword=hashed_pw
                                        )
                                        db.session.add(new_lecturer)
                                        db.session.commit()
                                        lecturer_records_added += 1
                                except Exception as row_err:
                                    print(f"[Row Error] {row_err}")
                        except Exception as sheet_err:
                            print(f"[Sheet Error] {sheet_err}")

                    if lecturer_records_added > 0:
                        flash(f"Successful upload {lecturer_records_added} record(s)", 'success')
                    else:
                        flash("No data uploaded", 'error')

                    return redirect(url_for('admin_manageLecturer'))

                except Exception as e:
                    print(f"[File Processing Error] {e}")
                    flash('File processing error: File upload in wrong format', 'error')
                    return redirect(url_for('admin_manageLecturer'))
            else:
                flash("No file uploaded", 'error')
                return redirect(url_for('admin_manageLecturer'))

        elif form_type == 'manual':
            id_text = request.form.get('userid', '').strip()
            name_text = request.form.get('username', '').strip()
            email_text = request.form.get('email', '').strip()
            contact_text = request.form.get('contact', '').strip()
            gender_text = request.form.get('gender', '').strip()
            department_text = request.form.get('department', '').strip()
            role_text = request.form.get('role', '').strip()
            hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')

            valid, result = check_lecturer(id_text, email_text, contact_text)
            if not valid:
                flash(result, 'error')
                return render_template(
                    'adminPart/adminManageLecturer.html',
                    user_data=user_data,
                    department_data=department_data,
                    id_text=id_text,
                    name_text=name_text,
                    email_text=email_text,
                    contact_text=contact_text,
                    department_text=department_text,
                    role_text=role_text,gender_text=gender_text,
                    active_tab='admin_manageLecturertab'
                )

            new_lecturer = User(
                userId=id_text,
                userName=name_text.upper(),
                userDepartment=department_text.upper(),
                userLevel=role_map[role_text],
                userEmail=email_text,
                userContact=contact_text,
                userGender=gender_text,
                userPassword=hashed_pw,
                userStatus=False
            )
            db.session.add(new_lecturer)
            db.session.commit()
            flash("New Lecturer Added Successfully", "success")
            return redirect(url_for('admin_manageLecturer'))

    return render_template(
        'adminPart/adminManageLecturer.html',
        active_tab='admin_manageLecturertab',
        user_data=user_data,
        department_data=department_data
    )






# function for admin to manage course information (adding, editing, and removing)
@app.route('/adminHome/manageCourse', methods=['GET', 'POST'])
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

                            df.columns = ['department code', 'course code', 'course section', 'course name', 'credit hour', 'practical lecturer', 'tutorial lecturer', 'no of students']

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

                                    valid, result = check_course(courseCode_text, courseSection_text, courseHour_text)
                                    if valid:
                                        new_course = Course(
                                            courseDepartment=department_text.upper(),
                                            courseCodeSection=courseCodeSection_text.upper(),
                                            courseCode=courseCode_text.upper(),
                                            courseSection=courseSection_text.upper(),
                                            courseName=courseName_text.upper(),
                                            courseHour=courseHour_text,
                                            coursePractical=coursePractical_text.upper(),
                                            courseTutorial=courseTutorial_text.upper(),
                                            courseStudent=courseStudent_text
                                        )
                                        db.session.add(new_course)
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

        elif form_type == 'manual':
            courseDepartment_text = request.form.get('courseDepartment', '').strip()
            department_text = courseDepartment_text.split('-')[0].strip()
            courseCode_text = request.form.get('courseCode', '').strip()
            courseSection_text = request.form.get('courseSection', '').strip()
            courseName_text = request.form.get('courseName', '').strip()
            courseHour_text = request.form.get('courseHour', '').strip()
            coursePractical_text = request.form.get('coursePractical', '').strip()
            courseTutorial_text = request.form.get('courseTutorial', '').strip()
            courseStudent_text = request.form.get('courseStudent', '').strip()
            courseCodeSection_text = courseCode_text + '/' + courseSection_text

            valid, result = check_course(courseCode_text, courseSection_text, courseHour_text)
            if not valid:
                flash(result, 'error')
                return render_template('adminPart/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, department_data=department_data, courseDepartment_text=courseDepartment_text,
                                        courseCode_text=courseCode_text, courseSection_text=courseSection_text, courseName_text=courseName_text, courseHour_text=courseHour_text, coursePractical=coursePractical_text,
                                        courseTutorial=courseTutorial_text, courseStudent_text=courseStudent_text)

            new_course = Course(
                courseDepartment=department_text.upper(),
                courseCodeSection=courseCodeSection_text.upper(),
                courseCode=courseCode_text.upper(),
                courseSection=courseSection_text.upper(),
                courseName=courseName_text.upper(),
                courseHour=courseHour_text,
                coursePractical=coursePractical_text.upper(),
                courseTutorial=courseTutorial_text.upper(),
                courseStudent=courseStudent_text
            )
            db.session.add(new_course)
            db.session.commit()
            flash("New Course Added Successfully", "success")
            return redirect(url_for('admin_manageCourse'))

    return render_template('adminPart/adminManageCourse.html', active_tab='admin_manageCoursetab', course_data=course_data, department_data=department_data)



# Function for admin to manage exam information (adding, editing, and removing)
@app.route('/adminHome/manageExam', methods=['GET', 'POST'])
def admin_manageExam():
    exam_data = Exam.query.all()
    department_data = Department.query.all() # For department code dropdown
    lecturer_data = User.query.filter(User.userLevel == 1).all() # Maybe can be delete
    venue_data = Venue.query.filter(Venue.venueStatus == 'AVAILABLE').all() # For venue selection dropdown
    course_data = Course.query.all() # For course selection dropdown and show out related tutorial, practical, and number of students

    # Default values for manual form
    examDate_text = ''
    examDay_text = ''
    startTime_text = ''
    endTime_text = ''
    programCode_text = ''
    courseSection_text = ''
    practicalLecturer_text = ''
    tutorialLecturer_text = ''
    student_text = ''
    venue_text = ''
    courseSection_text = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ===== File Upload =====
        if form_type == 'upload':
            file = request.files.get('exam_file')
            print(f"Read file: {file}")
            if file and file.filename:
                try:
                    file_stream = BytesIO(file.read())
                    excel_file = pd.ExcelFile(file_stream)

                    exam_records_added = 0
                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(
                                excel_file,
                                sheet_name=sheet_name,
                                usecols="A:J",
                                skiprows=1
                            )
                            df.columns = [str(col).strip().lower() for col in df.columns]
                            expected_cols = ['date', 'day', 'start', 'end', 'program', 'course/sec', 'practical lecturer', 'tutorial lecturer', 'no of', 'room']
                            print(f"Read file table: {expected_cols}")
                            if df.columns.tolist() != expected_cols:
                                raise ValueError("Excel columns do not match expected format")
                            df.columns = ['date', 'day', 'start', 'end', 'program', 'course/sec', 'practical lecturer', 'tutorial lecturer', 'no of', 'room']

                            for index, row in df.iterrows():
                                try:
                                    examDate_text = parse_date(row['date'])
                                    examDay_text = str(row['day']).upper()
                                    startTime_text = str(row['start']).upper()
                                    endTime_text = str(row['end']).upper()
                                    programCode_text = str(row['program']).upper()
                                    courseSection_text = str(row['course/sec']).upper()
                                    practicalLecturer_text = str(row['practical lecturer']).upper()
                                    tutorialLecturer_text = str(row['tutorial lecturer']).upper()
                                    student_text = row['no of']
                                    venue_text = str(row['room']).upper()

                                    valid, result = check_exam(courseSection_text, examDate_text, startTime_text, endTime_text)
                                    if valid:
                                        new_exam = Exam(
                                            examDate=examDate_text,
                                            examDay=examDay_text,
                                            examStartTime=startTime_text,
                                            examEndTime=endTime_text,
                                            examProgramCode=programCode_text,
                                            examCourseSectionCode=courseSection_text,
                                            examPracticalLecturer=practicalLecturer_text,
                                            examTutorialLecturer=tutorialLecturer_text,
                                            examTotalStudent=student_text,
                                            examVenue=venue_text
                                        )
                                        db.session.add(new_exam)
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

        # ===== Manual Add =====
        elif form_type == 'manual':
            try:
                examDate_text_raw = request.form.get('examDate', '').strip()
                examDate_text = parse_date(examDate_text_raw)
                examDay_text = request.form.get('examDay', '').strip()
                startTime_text = request.form.get('startTime', '').strip()
                endTime_text = request.form.get('endTime', '').strip()
                programCode_text = request.form.get('programCode', '').strip()
                courseSection_text = request.form.get('courseSection', '').strip()
                practicalLecturer_text = request.form.get('practicalLecturer', '').strip()
                tutorialLecturer_text = request.form.get('tutorialLecturer', '').strip()
                student_text = request.form.get('student', '').strip()
                venue_text = request.form.get('venue', '').strip()

                # Filter course list for re-rendering form in case of error
                '''if programCode_text:
                    course_data = Course.query.filter_by(courseDepartment=programCode_text).all()
                    print(f"Show me the courseSection_text: {courseSection_text}")

                    if courseSection_text:
                        selected_course = Course.query.filter_by(
                            courseDepartment=programCode_text,
                            courseCodeSection=courseSection_text
                        ).first()

                        if selected_course:
                            practicalLecturer_text = selected_course.coursePractical
                            tutorialLecturer_text = selected_course.courseTutorial
                            student_text = selected_course.courseStudent
                else:
                    course_data = Course.query.all()'''

                valid, result = check_exam(courseSection_text, examDate_text, startTime_text, endTime_text)
                if not valid:
                    flash(result, 'error')
                    return render_template('adminPart/adminManageExam.html',
                                           exam_data=exam_data, course_data=course_data, venue_data=venue_data,
                                           lecturer_data=lecturer_data, department_data=department_data,
                                           examDate_text=examDate_text, examDay_text=examDay_text,
                                           startTime_text=startTime_text, endTime_text=endTime_text,
                                           programCode_text=programCode_text, courseSection_text=courseSection_text,
                                           practicalLecturer_text=practicalLecturer_text, tutorialLecturer_text=tutorialLecturer_text, 
                                           student_text=student_text, venue_text=venue_text,
                                           active_tab='admin_manageExamtab')

                new_exam = Exam(
                    examDate=examDate_text,
                    examDay=examDay_text,
                    examStartTime=startTime_text,
                    examEndTime=endTime_text,
                    examProgramCode=programCode_text,
                    examCourseSectionCode=courseSection_text,
                    examPracticalLecturer=practicalLecturer_text,
                    examTutorialLecturer=tutorialLecturer_text,
                    examTotalStudent=student_text,
                    examVenue=venue_text
                )

                db.session.add(new_exam)
                db.session.commit()
                flash("New Exam Record Added Successfully", "success")
                return redirect(url_for('admin_manageExam'))

            except Exception as manual_err:
                print(f"[Manual Form Error] {manual_err}")
                flash("Error processing manual form", 'error')
                return redirect(url_for('admin_manageExam'))

    return render_template('adminPart/adminManageExam.html',
                           active_tab='admin_manageExamtab',
                           exam_data=exam_data,
                           course_data=course_data,
                           venue_data=venue_data,
                           lecturer_data=lecturer_data,
                           department_data=department_data)





# ===== New helper route for dependent dropdown =====
@app.route('/get_courses_by_department/<department_code>')
def get_courses_by_department(department_code):
    courses = Course.query.filter_by(courseDepartment=department_code).all()
    course_list = [{"courseCodeSection": c.courseCodeSection} for c in courses]
    return jsonify(course_list)



@app.route('/get_course_details/<program_code>/<course_code_section>')
def get_course_details(program_code, course_code_section):
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
