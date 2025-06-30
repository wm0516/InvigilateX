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
@app.route('/adminHome/uploadLecturerTimetable', methods=['GET', 'POST'])
def admin_uploadLecturerTimetable():
    user_data = User.query.all()

    if request.method == 'POST':
        if 'timetable_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['timetable_file']
        file_stream = BytesIO(file.read())

        lecturer_records_added = 0
        processed_records = []
        errors = []

        try:
            excel_file = pd.ExcelFile(file_stream)
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols="A:F",
                        skiprows=1
                    )
                    df.columns = ['Id', 'Name', 'Department', 'Role', 'Email', 'Contact']
                    df.reset_index(drop=True, inplace=True)

                    role_mapping = {
                        'lecturer': 1,
                        'hop': 2,
                        'dean': 3,
                        'admin': 4
                    }

                    for index, row in df.iterrows():
                        try:
                            lecturer_id = str(row['Id'])
                            lecturer_name = str(row['Name']).upper()
                            lecturer_department = str(row['Department']).upper()    
                            lecturer_email = str(row['Email'])
                            lecturer_contact = int(row['Contact'])
                            # Normalize and map role string
                            lecturer_role_str = str(row['Role']).strip().lower()
                            lecturer_role = role_mapping.get(lecturer_role_str)
                            
                            is_valid, error_message = unique_LecturerDetails(
                                lecturer_id, lecturer_email, lecturer_contact
                            )

                            if not is_valid:
                                row_number = index + 2 if isinstance(index, int) else str(index)
                                errors.append(f"Row {row_number} in sheet '{sheet_name}' error: {error_message}")
                                continue
                            
                            lecturer = User(
                                userId = lecturer_id,
                                userName = lecturer_name,
                                userDepartment = lecturer_department,
                                userLevel = lecturer_role,
                                userEmail = lecturer_email,
                                userContact = lecturer_contact,
                                userStatus = False
                            )

                            db.session.add(lecturer)
                            lecturer_records_added += 1

                            processed_records.append({
                                'ID': lecturer.userId,
                                'Name': lecturer.userName,
                                'Department': lecturer.userDepartment,
                                'Role': lecturer.userLevel,
                                'Email': lecturer.userEmail,
                                'Contact': lecturer.userContact,
                                'Status': lecturer.userStatus
                            })

                        except Exception as row_err:
                            pass

                    db.session.commit()

                except Exception as sheet_err:
                    pass
            # Final response
            if is_valid and lecturer_records_added > 0:
                message = f"Successful upload {lecturer_records_added} record(s)"
                flash(message, 'success')
            else:
                message = "No data uploaded"
                flash(message, 'error')
            return redirect(url_for('admin_uploadLecturerTimetable'))
        


        except Exception as e:
            flash('File processing error: File upload in wrong format','error')
            return redirect(url_for('admin_uploadLecturerTimetable'))
        
    return render_template('adminPart/adminUploadLecturerTimetable.html', active_tab='admin_uploadLecturerTimetabletab', user_data=user_data)





# function for admin manage invigilation timetable for all lecturer based on their availability (adding, editing, and removing)
@app.route('/adminhome/manageInvigilationTimetable', methods=['GET', 'POST'])
def admin_manageInvigilationTimetable():
    exam_data = Exam.query.all()
    user_data = User.query.all()
    department_data = Department.query.all()
    ratios = request.form.getlist("ratio[]")
    deptcodes = request.form.getlist("deptcode[]")

    if request.method == 'POST':
        # Pair department codes and ratios into a list of dicts
        data = [
            {"departmentCode": code, "ratio": int(ratio) if ratio else None}
            for code, ratio in zip(deptcodes, ratios)
        ]

        # Loop through each pair and update the corresponding department
        for item in data:
            dept = Department.query.filter_by(departmentCode=item["departmentCode"]).first()
            if dept:
                dept.departmentRatio = item["ratio"]

        db.session.commit()
        flash("Department ratios updated successfully.", "success")
        return redirect(url_for('admin_manageInvigilationTimetable'))


    return render_template('adminPart/adminManageInvigilationTimetable.html', active_tab='admin_manageInvigilationTimetabletab', 
                           user_data=user_data, exam_data=exam_data, department_data=department_data)




































# Can move those validation into a function then call again
@app.route('/adminHome/profile', methods=['GET', 'POST'])
def admin_profile():
    adminId = session.get('user_id')
    admin = User.query.filter_by(userId=adminId).first()
    
    # Pre-fill existing data
    adminContact_text = ''
    adminPassword1_text = ''
    adminPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        adminContact_text = request.form.get('contact', '').strip()
        adminPassword1_text = request.form.get('password1', '').strip()
        adminPassword2_text = request.form.get('password2', '').strip()
        is_valid, message = check_contact(adminContact_text)

        # Error checks
        if adminContact_text and not contact_format(adminContact_text):
            error_message = "Wrong Contact Number format"
        elif adminContact_text and not is_valid:
            error_message = message
        elif adminPassword1_text or adminPassword2_text:
            if adminPassword1_text != adminPassword2_text:
                error_message = "Passwords do not match."

        if error_message:
            flash(str(error_message), 'error')
        elif not adminContact_text and not adminPassword1_text:
            flash("Nothing to update", 'error')
        else:
            if admin:
                if adminContact_text:
                    admin.userContact = adminContact_text
                if adminPassword1_text:
                    hashed_pw = bcrypt.generate_password_hash(adminPassword1_text).decode('utf-8')
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
        admin_role_text={
            LECTURER: "Lecturer",
            HOP: "Hop",
            DEAN: "Dean",
            ADMIN: "Admin"
        }.get(admin.userLevel, "Unknown") if admin else '',
        adminContact_text=adminContact_text,
        adminPassword1_text=adminPassword1_text,
        adminPassword2_text=adminPassword2_text,
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
    id_text = ''
    name_text = ''
    email_text = ''
    contact_text = ''
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
        file = request.files['lecturer_file']
        file_stream = BytesIO(file.read())

        lecturer_records_added = 0

        if file and file.filename:
            try:
                excel_file = pd.ExcelFile(file_stream)
                print(f"Found sheets: {excel_file.sheet_names}")

                for sheet_name in excel_file.sheet_names:
                    try:
                        df = pd.read_excel(
                            excel_file,
                            sheet_name=sheet_name,
                            usecols="A:F",
                            skiprows=1
                        )

                        # Debugging: show raw column headers
                        print(f"Raw columns from sheet '{sheet_name}': {df.columns.tolist()}")

                        # Clean and standardize columns
                        df.columns = [str(col).strip().lower() for col in df.columns] 
                        expected_cols = ['id', 'name', 'department', 'role', 'email', 'contact']

                        if df.columns.tolist() != expected_cols:
                            raise ValueError("Excel columns do not match the expected format: " + str(df.columns.tolist()))

                        # Rename to match your model
                        df.columns = ['id', 'name', 'department', 'role', 'email', 'contact']
                        print(f"Data read from excel:\n{df.head()}")

                        role_mapping = {
                            'lecturer': 1,
                            'hop': 2,
                            'dean': 3,
                            'admin': 4
                        }

                        for index, row in df.iterrows():
                            try:
                                id_text = str(row['Id'])
                                name_text = str(row['Name']).upper()
                                department_text = str(row['Department']).upper()    
                                email_text = str(row['Email'])
                                contact_text = int(row['Contact'])
                                # Normalize and map role string
                                role_text_str = str(row['Role']).strip().lower()
                                role_text = role_mapping.get(role_text_str)
                                hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')
                                
                                valid, result = check_lecturer(id_text, email_text, contact_text, name_text, department_text, role_text)

                                if valid:
                                    new_lecturer = User(
                                        userId = id_text,
                                        userName = name_text,
                                        userDepartment = department_text,
                                        userLevel = role_text,
                                        userEmail = email_text,
                                        userContact = contact_text,
                                        userStatus = False,
                                        userPassword = hashed_pw
                                    )

                                    db.session.add(new_lecturer)
                                    lecturer_records_added += 1
                                    db.session.commit()
                            except Exception as row_err:
                                print(f"[Row Error] {row_err}")
                    except Exception as sheet_err:
                        print(f"[Sheet Error] {sheet_err}")  # <-- Print or log this

                if lecturer_records_added > 0:
                    flash(f"Successful upload {lecturer_records_added} record(s)", 'success')
                else:
                    flash("No data uploaded", 'error')

                return redirect(url_for('admin_manageLecturer'))

            except Exception as e:
                print(f"[File Processing Error] {e}")  # <-- See the actual cause
                flash('File processing error: File upload in wrong format', 'error')
                return redirect(url_for('admin_manageLecturer'))
            
        else:
            # Handle manual input
            id_text = request.form.get('userid', '').strip()
            name_text = request.form.get('username', '').strip()
            email_text = request.form.get('email', '').strip()
            contact_text = request.form.get('contact', '').strip()
            department_text = request.form.get('department', '').strip()
            role_text = request.form.get('role', '').strip()
            hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')

            valid, result = check_lecturer(id_text, email_text, contact_text, name_text, department_text, role_text)
            if not valid:
                flash(result, 'error')
                return render_template('adminPart/adminManageLecturer.html', user_data=user_data, department_data=department_data,
                                        id_text=id_text, name_text=name_text, email_text=email_text, contact_text=contact_text, 
                                        department_text=department_text, role_text=role_text, active_tab='admin_manageLecturertab')

            new_lecturer = User(
                userId=id_text,
                userName=name_text.upper(),
                userDepartment=department_text.upper(),
                userLevel=role_map[role_text],  # use mapped constant
                userEmail=email_text,
                userContact=contact_text,
                userPassword=hashed_pw,
                userStatus=False
            )
            db.session.add(new_lecturer)
            db.session.commit()
            flash("New Lecturer Added Successfully", "success")
            return redirect(url_for('admin_manageLecturer'))

    return render_template('adminPart/adminManageLecturer.html', active_tab='admin_manageLecturertab', user_data=user_data, department_data=department_data)


# function for admin to manage course information (adding, editing, and removing)
@app.route('/adminHome/manageCourse', methods=['GET', 'POST'])
def admin_manageCourse():
    course_data = Course.query.all()
    courseCode_text = ''
    courseSection_text = ''
    courseName_text = ''
    courseHour_text = ''

    if request.method == 'POST':
        file = request.files['course_file']
        file_stream = BytesIO(file.read())

        course_records_added = 0  # <-- Make sure this is initialized

        if file and file.filename:
            try:
                excel_file = pd.ExcelFile(file_stream)
                print(f"Found sheets: {excel_file.sheet_names}")

                for sheet_name in excel_file.sheet_names:
                    try:
                        df = pd.read_excel(
                            excel_file,
                            sheet_name=sheet_name,
                            usecols="A:D",
                            skiprows=1
                        )

                        # Debugging: show raw column headers
                        print(f"Raw columns from sheet '{sheet_name}': {df.columns.tolist()}")

                        # Clean and standardize columns
                        df.columns = [str(col).strip().lower() for col in df.columns] 
                        expected_cols = ['code', 'section', 'name', 'credithour']

                        if df.columns.tolist() != expected_cols:
                            raise ValueError("Excel columns do not match the expected format: " + str(df.columns.tolist()))

                        # Rename to match your model
                        df.columns = ['code', 'section', 'name', 'creditHour']
                        print(f"Data read from excel:\n{df.head()}")

                        for index, row in df.iterrows():
                            try:
                                courseCode_text = str(row['code']).upper()
                                courseSection_text = str(row['section']).upper()
                                courseName_text = str(row['name']).upper()
                                courseHour_text = int(row['creditHour'])
                                courseCodeSection_text = (courseCode_text + '/' + courseSection_text).upper()

                                valid, result = check_course(courseCode_text, courseSection_text, courseName_text, courseHour_text)
                                if valid:
                                    new_course = Course(
                                        courseCodeSection = courseCodeSection_text,
                                        courseCode=courseCode_text.upper(),
                                        courseSection=courseSection_text.upper(),
                                        courseName=courseName_text.upper(),
                                        courseHour=courseHour_text
                                    )
                                    db.session.add(new_course)
                                    course_records_added += 1
                                    db.session.commit()
                            except Exception as row_err:
                                print(f"[Row Error] {row_err}")
                    except Exception as sheet_err:
                        print(f"[Sheet Error] {sheet_err}")  # <-- Print or log this

                if course_records_added > 0:
                    flash(f"Successful upload {course_records_added} record(s)", 'success')
                else:
                    flash("No data uploaded", 'error')

                return redirect(url_for('admin_manageCourse'))

            except Exception as e:
                print(f"[File Processing Error] {e}")  # <-- See the actual cause
                flash('File processing error: File upload in wrong format', 'error')
                return redirect(url_for('admin_manageCourse'))
        
        else:
            # Handle manual input
            courseCode_text = request.form.get('courseCode', '').strip()
            courseSection_text = request.form.get('courseSection', '').strip()
            courseName_text = request.form.get('courseName', '').strip()
            courseHour_text = request.form.get('courseHour', '').strip()
            courseCodeSection_text = (courseCode_text + '/' + courseSection_text).upper()

            valid, result = check_course(courseCode_text, courseSection_text, courseName_text, courseHour_text)
            if not valid:
                flash(result, 'error')
                return render_template('adminPart/adminManageCourse.html', 
                                        course_data=course_data,
                                        courseCode_text=courseCode_text,
                                        courseSection_text=courseSection_text,
                                        courseName_text=courseName_text,
                                        courseHour_text=courseHour_text,
                                        active_tab='admin_manageCoursetab')
            
            try:
                hour_int = int(courseHour_text)
            except ValueError:
                flash("Course Hour must be a valid integer.", 'error')
                return render_template('adminPart/adminManageCourse.html', 
                                        course_data=course_data,
                                        courseCode_text=courseCode_text,
                                        courseSection_text=courseSection_text,
                                        courseName_text=courseName_text,
                                        courseHour_text=courseHour_text,
                                        active_tab='admin_manageCoursetab')

            new_course = Course(
                courseCodeSection = courseCodeSection_text,
                courseCode=courseCode_text.upper(),
                courseSection=courseSection_text.upper(),
                courseName=courseName_text.upper(),
                courseHour=hour_int
            )
            db.session.add(new_course)
            db.session.commit()
            flash("New Course Added Successfully", "success")
            return redirect(url_for('admin_manageCourse'))

    return render_template('adminPart/adminManageCourse.html',
                           active_tab='admin_manageCoursetab',
                           course_data=course_data)


# function for admin to manage exam information (adding, editing, adn removing)
@app.route('/adminHome/manageExam', methods=['GET', 'POST'])
def admin_manageExam():
    exam_data = Exam.query.all()
    examDate_text = ''
    examDay_text = ''
    startTime_text = ''
    endTime_text = ''
    programCode_text = ''
    courseSection_text = ''
    lecturer_text = ''
    student_text = ''
    venue_text = ''

    if request.method == 'POST':
        print('1 yes get post')
        file = request.files['exam_file']
        file_stream = BytesIO(file.read())
        exam_records_added = 0  # <-- Make sure this is initialized
        print('request.files:', request.files)
        print('exam_file' in request.files)
        print('file.filename:', file.filename)
        
        if file and file.filename:
            print('2 yes get post')
            try:
                excel_file = pd.ExcelFile(file_stream)
                print(f"Found sheets: {excel_file.sheet_names}")
                for sheet_name in excel_file.sheet_names:
                    try:
                        df = pd.read_excel(
                            excel_file,
                            sheet_name=sheet_name,
                            usecols="A:I",
                            skiprows=1
                        )
                        # Debugging: show raw column headers
                        print(f"Raw columns from sheet '{sheet_name}': {df.columns.tolist()}")

                         # Clean and standardize columns
                        df.columns = [str(col).strip().lower() for col in df.columns]
                        # print("Detected columns:", df.columns.tolist())
                        expected_cols = ['date', 'day', 'start', 'end', 'program', 'course/sec', 'lecturer', 'no of', 'room']

                        if df.columns.tolist() != expected_cols:
                            raise ValueError("Excel columns do not match the expected format: " + str(df.columns.tolist()))

                        # Rename to match your model
                        df.columns = ['date', 'day', 'start', 'end', 'program', 'course/sec', 'lecturer', 'no of', 'room']
                        print(f"Data read from excel:\n{df.head()}")

                        for index, row in df.iterrows():
                            try:
                                examDate_text = parse_date(row['Date'])
                                examDay_text = str(row['Day']).upper()
                                startTime_text = str(row['Start']).upper()
                                endTime_text = str(row['End']).upper()
                                programCode_text = str(row['Program']).upper()
                                courseSection_text = str(row['Course/Sec']).upper()
                                lecturer_text = str(row['Lecturer']).upper()
                                student_text = row['No Of']
                                venue_text = str(row['Room']).upper()

                                print(f"Row {index}: {examDate_text}, {examDay_text}, {startTime_text}, {endTime_text}, {programCode_text}, {courseSection_text}, {lecturer_text}, {student_text}, {venue_text}")

                                valid, result = check_exam(courseSection_text, examDate_text, startTime_text, endTime_text, examDay_text, programCode_text, lecturer_text, student_text, venue_text)
                                if valid:
                                    new_exam= Exam(
                                        examDate = examDate_text,
                                        examDay = examDay_text,
                                        examStartTime = startTime_text,
                                        examEndTime = endTime_text,
                                        examProgramCode = programCode_text,
                                        examCourseSectionCode = courseSection_text,
                                        examLecturer = lecturer_text,
                                        examTotalStudent = student_text,
                                        examVenue = venue_text
                                    )
                                    db.session.add(new_exam)
                                    exam_records_added += 1
                                    db.session.commit()
                            except Exception as row_err:
                                print(f"[Row Error] {row_err}")
                    except Exception as sheet_err:
                        print(f"[Sheet Error] {sheet_err}")  # <-- Print or log this

                if exam_records_added > 0:
                    flash(f"Successful upload {exam_records_added} record(s)", 'success')
                else:
                    flash("No data uploaded", 'error')

                return redirect(url_for('admin_manageExam'))

            except Exception as e:
                print(f"[Manual Input Error] {e}")
                flash('Manual input error. Please check your input format.', 'error')
                print(f"[File Processing Error] {e}")  # <-- See the actual cause
                flash('File processing error: File upload in wrong format', 'error')
                return redirect(url_for('admin_manageExam'))
        
        else:
            # Handle manual input
            examDate_text_raw = request.form.get('examDate', '').strip()
            print("Submitted examDate_text_raw:", examDate_text_raw)
            examDate_text = parse_date(examDate_text_raw)
            print("Parsed examDate_text:", examDate_text)

            examDay_text = request.form.get('examDay', '').strip()
            startTime_text = request.form.get('startTime', '').strip()
            endTime_text = request.form.get('endTime', '').strip()
            programCode_text = request.form.get('programCode', '').strip()
            courseSection_text = request.form.get('courseSection', '').strip()
            lecturer_text = request.form.get('lecturer', '').strip()
            student_text = request.form.get('student', '').strip()
            venue_text = request.form.get('venue', '').strip()

            valid, result = check_exam(courseSection_text, examDate_text, startTime_text, endTime_text, examDay_text, programCode_text, lecturer_text, student_text, venue_text)
            if not valid:
                flash(result, 'error')
                return render_template('adminPart/adminManageExam.html', exam_data=exam_data, examDate_text=examDate_text, examDay_text=examDay_text,
                                        startTime_text=startTime_text, endTime_text=endTime_text, programCode_text=programCode_text, courseSection_text=courseSection_text,
                                        lecturer_text=lecturer_text, student_text=student_text, venue_text=venue_text, active_tab='admin_manageExamtab')
        
            new_exam= Exam(
                examDate = examDate_text,
                examDay = examDay_text,
                examStartTime = startTime_text,
                examEndTime = endTime_text,
                examProgramCode = programCode_text,
                examCourseSectionCode = courseSection_text,
                examLecturer = lecturer_text,
                examTotalStudent = student_text,
                examVenue = venue_text
            )
            db.session.add(new_exam)
            db.session.commit()
            flash("New Course Added Successfully", "success")
            return redirect(url_for('admin_manageExam'))

    return render_template('adminPart/adminManageExam.html', active_tab='admin_manageExamtab', exam_data=exam_data)


# function for admin to manage department information (adding, editing, and removing)
@app.route('/adminHome/manageDepartment', methods=['GET', 'POST'])
def admin_manageDepartment():
    department_data = Department.query.all()
    departmentCode_text = ''
    departmentName_text = ''
    departmentRatio_text = ''

    if request.method == 'POST':
        departmentCode_text = request.form.get('departmentCode', '').strip()
        departmentName_text = request.form.get('departmentName', '').strip()
        departmentRatio_text = request.form.get('departmentRatio', '').strip()

        valid, result = check_department(departmentCode_text, departmentName_text)
        if not valid:
            flash(result, 'error')
            return render_template('adminPart/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data, departmentCode_text=departmentCode_text, 
                                   departmentRatio_text=departmentRatio_text, departmentName_text=departmentName_text)

        new_department = Department(
            departmentCode=departmentCode_text.upper(),
            departmentName=departmentName_text.upper(),
            departmentRatio=departmentRatio_text
        )
        db.session.add(new_department)
        db.session.commit()
        flash("New Department Added Successfully", "success")
        return redirect(url_for('admin_manageDepartment'))

    return render_template('adminPart/adminManageDepartment.html', active_tab='admin_manageDepartmenttab', department_data=department_data)












