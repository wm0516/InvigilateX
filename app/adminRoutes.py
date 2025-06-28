from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app import app
from .backend import *
from .database import *
import os
from io import BytesIO
import pandas as pd
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()



@app.route('/home/autoGenerate', methods=['GET', 'POST'])
def admin_autoGenerate():
    exam_data = ExamDetails.query.all()
    department_data = Department.query.all()
    return render_template('adminPart/adminAutoSchedule.html', active_tab='admin_autoGeneratetab', exam_data=exam_data, department_data=department_data)

@app.route('/adminHome/manageLecturer')
def admin_manageLecturer():
    user_data = User.query.all()
    return render_template('adminPart/adminManageLecturer.html', active_tab='admin_manageLecturertab', user_data=user_data)


@app.route('/adminHome/invigilationReport', methods=['GET', 'POST'])
def admin_viewReport():
    return render_template('adminPart/adminInvigilationReport.html', active_tab='admin_viewReporttab')


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

                                if not courseCode_text or not courseName_text or not isinstance(courseHour_text, (int, float)):
                                    continue

                                valid, result = check_course(courseCode_text, courseSection_text, courseName_text, courseHour_text)
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





UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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


@app.route('/adminHome/uploadExamDetails', methods=['GET', 'POST'])
def admin_uploadExamDetails():
    exam_data = ExamDetails.query.all()

    if request.method == 'POST':
        if 'exam_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['exam_file']
        file_stream = BytesIO(file.read())

        exam_records_added = 0
        processed_records = []
        errors = []

        try:
            excel_file = pd.ExcelFile(file_stream)

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols="A:I",
                        skiprows=1
                    )
                    df.columns = ['Date', 'Day', 'Start', 'End', 'Program', 'Course/Sec', 'Lecturer', 'No Of', 'Room']
                    df.reset_index(drop=True, inplace=True)

                    for index, row in df.iterrows():
                        try:
                            exam_date = pd.to_datetime(row['Date']).date()
                            exam_start = str(row['Start'])
                            exam_end = str(row['End'])
                            exam_course = row['Course/Sec']

                            is_valid, error_message = unique_examDetails(
                                exam_course, exam_date, exam_start, exam_end
                            )

                            if not is_valid:
                                row_number = index + 2 if isinstance(index, int) else str(index)
                                errors.append(f"Row {row_number} in sheet '{sheet_name}' error: {error_message}")
                                continue

                            exam = ExamDetails(
                                examDate=exam_date,
                                examDay=row['Day'],
                                examStartTime=exam_start,
                                examEndTime=exam_end,
                                examProgramCode=row['Program'],
                                examCourseSectionCode=exam_course,
                                examLecturer=row['Lecturer'],
                                examTotalStudent=int(row['No Of']),
                                examVenue=row['Room'] if pd.notna(row['Room']) else ''
                            )

                            db.session.add(exam)
                            exam_records_added += 1

                            processed_records.append({
                                'Date': exam.examDate.strftime('%Y-%m-%d'),
                                'Day': exam.examDay,
                                'Start': exam.examStartTime,
                                'End': exam.examEndTime,
                                'Program': exam.examProgramCode,
                                'Course/Sec': exam.examCourseSectionCode,
                                'Lecturer': exam.examLecturer,
                                'No Of': exam.examTotalStudent,
                                'Room': exam.examVenue
                            })

                        except Exception as row_err:
                            pass

                    db.session.commit()

                except Exception as sheet_err:
                    pass
            # Final response
            if is_valid and exam_records_added > 0:
                message = f"Successful upload {exam_records_added} record(s)"
                flash(message, 'success')
            else:
                message = "No data uploaded"
                flash(message, 'error')

        except Exception as e:
            flash('File processing error: File upload in wrong format','error')
            return redirect(url_for('admin_uploadExamDetails'))

    return render_template('adminPart/adminUploadExamDetails.html', active_tab='admin_uploadExamDetailstab', exam_data=exam_data)


@app.route('/adminHome/uploadLecturerList', methods=['GET', 'POST'])
def admin_uploadLecturerList():        
    user_data = User.query.all()
    
    if request.method == 'POST':
        if 'lecturer_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['lecturer_file']
        file_stream = BytesIO(file.read())

        lecturer_list_added = 0
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
                            hashed_pw = bcrypt.generate_password_hash('Abc12345!').decode('utf-8')
                            
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
                                userStatus = False,
                                userPassword = hashed_pw
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
            return redirect(url_for('admin_uploadLecturerList'))

        except Exception as e:
            flash('File processing error: File upload in wrong format','error')
            return redirect(url_for('admin_uploadLecturerList'))

    return render_template('adminPart/adminUploadLecturerList.html', active_tab='admin_uploadLecturerListtab', user_data=user_data)





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








