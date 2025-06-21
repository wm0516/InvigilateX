from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app import app
from .backend import *
from .database import *
import os
from io import BytesIO
import pandas as pd
from werkzeug.utils import secure_filename
from .backend import *
from .database import *
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

# Set the default link into admin_login, because this program have 3 login phase
@app.route('/')
def index():
    return redirect(url_for('admin_login'))

# login page (done with checking email address and hash password)
@app.route('/adminLogin', methods=['GET', 'POST'])
def admin_login():
    admin_login_text = ''
    admin_password_text = ''

    if request.method == 'POST':
        admin_login_text = request.form.get('textbox', '').strip()
        admin_password_text = request.form.get('password', '').strip()
        
        # First check for empty fields
        if not admin_login_text or not admin_password_text:
            flash("Please fill in all fields", 'input_error')  # Using 'input_error' category
            return render_template('adminPart/adminLogin.html', admin_login_text=admin_login_text, admin_password_text=admin_password_text)
        
        # Then check the login credentials
        valid, result = check_login('admin', admin_login_text, admin_password_text)
        if not valid:
            flash(result, 'input_error')  # Show it using flash
        else:
            session['admin_id'] = result
            return redirect(url_for('admin_homepage'))
        
    return render_template('adminPart/adminLogin.html', admin_login_text=admin_login_text, admin_password_text=admin_password_text)


# register page (done with all input validation and userID as Primary Key)
@app.route('/adminRegister', methods=['GET', 'POST'])
def admin_register():
    adminId_text = ''
    adminName_text = ''
    adminEmail_text = ''
    adminContact_text = ' '
    adminPassword1_text = ''
    adminPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        adminId_text = request.form.get('userid', '').strip()
        adminName_text = request.form.get('username', '').strip()
        adminEmail_text = request.form.get('email', '').strip()
        adminContact_text = request.form.get('contact', '').strip()
        adminPassword1_text = request.form.get('password1', '').strip()
        adminPassword2_text = request.form.get('password2', '').strip()

        # Use the new check_register function
        is_valid, error_message = check_register(adminId_text, adminEmail_text, adminContact_text)
        
        if not is_valid:
            pass  # error_message is already set
        elif not all([adminId_text, adminName_text, adminEmail_text, adminContact_text]):
            error_message = "All fields are required."
        elif not email_format(adminEmail_text):
            error_message = "Wrong Email Address format"
        elif not contact_format(adminContact_text):
            error_message = "Wrong Contact Number format"
        elif adminPassword1_text != adminPassword2_text:
            error_message = "Passwords do not match."
        elif not password_format(adminPassword1_text):
            error_message = "Wrong password format."

        if error_message:
            flash(error_message, 'error')
        else:
            hashed_pw = bcrypt.generate_password_hash(adminPassword1_text).decode('utf-8')
            new_admin = Admin(
                adminId = adminId_text,
                adminName = adminName_text.upper(),
                adminDepartment = 'Admin',
                adminEmail = adminEmail_text,
                adminContact = adminContact_text,
                adminPassword = hashed_pw
            )
            
            db.session.add(new_admin)
            db.session.commit()
            flash(f"Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('admin_login'))
        
    return render_template('adminPart/adminRegister.html', adminId_text=adminId_text, adminName_text=adminName_text, 
                           adminEmail_text=adminEmail_text, adminContact_text=adminContact_text, adminPassword1_text=adminPassword1_text, 
                           adminPassword2_text=adminPassword2_text, error_message=error_message)


# forgot password page (done when the email exist in database will send reset email link)
@app.route('/adminForgotPassword', methods=['GET', 'POST'])
def admin_forgotPassword():
    admin_forgot_email_text = ''
    error_message = None

    if request.method == 'POST':
        admin_forgot_email_text = request.form.get('email', '').strip()

        if not admin_forgot_email_text:
            error_message = "Email address is required."
        
        if error_message:
            flash(error_message, 'error')
        else:
            success, message = check_forgotPasswordEmail('admin', admin_forgot_email_text)
            if not success:
                error_message = message
                flash(str(error_message), 'error')
            else:
                flash("Reset link sent to your email address.", 'success')
                return redirect(url_for('admin_login'))

    return render_template('adminPart/adminForgotPassword.html', admin_forgot_email_text=admin_forgot_email_text, error_message=error_message)


# reset password page (done after reset password based on that user password)
@app.route('/adminResetPassword/<token>', methods=['GET', 'POST'])
def admin_resetPassword(token):
    admin_password_text_1 = ''
    admin_password_text_2 = ''
    error_message = None
    
    if request.method == 'POST':
        admin_password_text_1 = request.form.get('password1', '').strip()
        admin_password_text_2 = request.form.get('password2', '').strip()

        admin, error_message = check_resetPassword('admin', token, admin_password_text_1, admin_password_text_2)
        if error_message:
            flash(error_message, 'error')
        elif admin:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('admin_login'))
        
    return render_template('adminPart/adminResetPassword.html', admin_password_text_1=admin_password_text_1, 
                           admin_password_text_2=admin_password_text_2, error_message=error_message)


# Logout button from homepage to login page
@app.route('/adminLogout')
def admin_logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('admin_login')) 


# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_admin_data():
    adminId = session.get('admin_id')
    if adminId:
        admin = Admin.query.get(adminId)
        if admin:
            return {
                'admin_id': adminId,
                'admin_name': admin.adminName,
                'admin_department': admin.adminDepartment,
                'admin_email': admin.adminEmail,
                'admin_contact' : admin.adminContact
            }
    return {
        'admin_id': None,
        'admin_name': '',
        'admin_department': '',
        'admin_email': '',
        'admin_contact': ''
    }


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/adminHome', methods=['GET', 'POST'])
def admin_homepage():
    return render_template('adminPart/adminHomepage.html', active_tab='admin_hometab')

@app.route('/home/autoGenerate', methods=['GET', 'POST'])
def admin_autoGenerate():
    return render_template('adminPart/adminAutoSchedule.html', active_tab='admin_autoGeneratetab')

@app.route('/adminHome/manageLecturer')
def admin_manageLecturer():
    return render_template('adminPart/adminManageLecturer.html', active_tab='admin_managetab')

@app.route('/adminHome/upload')
def admin_upload():
    return render_template('adminPart/adminUpload.html', active_tab='admin_uploadtab')







UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
@app.route('/adminHome/uploadLecturerTimetable', methods=['GET', 'POST'])
def admin_uploadLecturerTimetable():
    if request.method == 'POST':
        # Validate file exists
        if 'lecturer_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file uploaded',
                'errors': ['No file was selected for upload']
            })

        file = request.files['lecturer_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected',
                'errors': ['Please select a valid file to upload']
            })

        # Validate file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm')):
            return jsonify({
                'success': False,
                'message': 'Invalid file type',
                'errors': ['Only Excel files (.xlsx, .xls, .xlsm) are accepted']
            })

        file_stream = BytesIO(file.read())
        lecturer_records_added = 0
        processed_records = []
        errors = []
        has_valid_records = False

        try:
            excel_file = pd.ExcelFile(file_stream)
            
            for sheet_name in excel_file.sheet_names:
                try:
                    # Read Excel with proper data types
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols="A:F",
                        skiprows=1,
                        dtype={
                            'Id': str,
                            'Name': str,
                            'Department': str,
                            'Role': str,
                            'Email': str,
                            'Contact': str
                        }
                    )
                    
                    # Clean column names and drop empty rows
                    df.columns = ['Id', 'Name', 'Department', 'Role', 'Email', 'Contact']
                    df = df.dropna(how='all')
                    df = df.fillna('')
                    df.reset_index(drop=True, inplace=True)

                    # Role mapping with case insensitivity
                    role_mapping = {
                        'lecturer': 1,
                        'dean': 2,
                        'admin': 3,
                        '1': 1,
                        '2': 2,
                        '3': 3
                    }

                    for index, row in df.iterrows():
                        try:
                            # Skip empty rows
                            if not row['Id'] and not row['Name']:
                                continue

                            # Process and validate each field
                            lecturer_id = str(row['Id']).strip()
                            lecturer_name = str(row['Name']).strip().upper()
                            lecturer_department = str(row['Department']).strip().upper()
                            lecturer_email = str(row['Email']).strip().lower()
                            lecturer_contact = str(row['Contact']).strip()
                            lecturer_role_str = str(row['Role']).strip().lower()
                            lecturer_role = role_mapping.get(lecturer_role_str, 1)  # Default to lecturer

                            # Validate contact (preserve leading zeros)
                            if not lecturer_contact.isdigit():
                                raise ValueError("Contact must contain only digits")
                            if len(lecturer_contact) < 9:
                                raise ValueError("Contact number too short")

                            # Check for duplicates
                            is_valid, error_message = unique_LecturerDetails(
                                lecturer_id, lecturer_email, lecturer_contact
                            )

                            if not is_valid:
                                raise ValueError(error_message)
                            
                            # Create new user record
                            lecturer = User(
                                userId=lecturer_id,
                                userName=lecturer_name,
                                userDepartment=lecturer_department,
                                userLevel=lecturer_role,
                                userEmail=lecturer_email,
                                userContact=lecturer_contact,
                                userStatus=False
                            )

                            db.session.add(lecturer)
                            lecturer_records_added += 1
                            has_valid_records = True

                            processed_records.append({
                                'ID': lecturer_id,
                                'Name': lecturer_name,
                                'Department': lecturer_department,
                                'Role': lecturer_role,
                                'Email': lecturer_email,
                                'Contact': lecturer_contact,
                                'Status': 'Deactivated'
                            })

                        except Exception as row_err:
                            row_number = index + 2  # +2 for header and 0-based index
                            errors.append(f"Row {row_number} in sheet '{sheet_name}': {str(row_err)}")
                            continue

                    db.session.commit()

                except Exception as sheet_err:
                    errors.append(f"Error processing sheet '{sheet_name}': {str(sheet_err)}")
                    continue

            # Prepare final response
            response_data = {
                'success': has_valid_records,
                'records': processed_records,
                'errors': errors
            }

            if has_valid_records:
                response_data['message'] = f"Successfully uploaded {lecturer_records_added} record(s)"
                if errors:
                    response_data['message'] += f" (with {len(errors)} warnings)"
            else:
                response_data['message'] = "No valid records uploaded" if not errors else "Upload failed"

            return jsonify(response_data)

        except Exception as e:
            current_app.logger.error(f"File processing error: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': "Error processing file",
                'errors': [f"System error: {str(e)}"]
            })
        
    # GET request - initial page load
    user_data = User.query.order_by(User.userName).all()
    return render_template('adminPart/adminUploadLecturerTimetable.html', 
                         active_tab='admin_uploadLecturerTimetabletab', 
                         user_data=user_data)


@app.route('/adminHome/uploadExamDetails', methods=['GET', 'POST'])
def admin_uploadExamDetails():
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
                success = True
            else:
                message = "No data uploaded"
                success = False

            return jsonify({
                'success': success,
                'message': message,
                'records': processed_records,
                'errors': errors
            })

        except Exception as e:
            current_app.logger.error("File processing error: File upload in wrong format")
            return jsonify({'success': False, 'message': "Error processing file: File upload in wrong format"})

    # GET request
    exam_data = ExamDetails.query.all()
    return render_template('adminPart/adminUploadExamDetails.html', active_tab='admin_uploadExamDetailstab', exam_data=exam_data)


@app.route('/adminHome/uploadLecturerList', methods=['GET', 'POST'])
def admin_uploadLecturerList():
    if request.method == 'POST':
        if 'lecturerList_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['lecturerList_file']
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
                        'dean': 2,
                        'admin': 3
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
                success = True
            else:
                message = "No data uploaded"
                success = False

            return jsonify({
                'success': success,
                'message': message,
                'records': processed_records,
                'errors': errors
            })

        except Exception as e:
            current_app.logger.error("File processing error: File upload in wrong format")
            return jsonify({'success': False, 'message': "Error processing file: File upload in wrong format"})
        
    user_data = User.query.all()
    return render_template('adminPart/adminUploadLecturerList.html', active_tab='admin_uploadLecturerListtab', user_data=user_data)

@app.route('/adminHome/uploadCourseDetails', methods=['GET', 'POST'])
def admin_uploadCourseDetails():
    return render_template('adminPart/adminUploadCourseDetails.html', active_tab='admin_uploadCourseDetailstab')




@app.route('/adminHome/profile', methods=['GET', 'POST'])
def admin_profile():
    adminId = session.get('admin_id')
    admin = Admin.query.filter_by(adminId=adminId).first()
    
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
            flash("Nothing to update", 'info')
        else:
            if admin:
                if adminContact_text:
                    admin.adminContact = adminContact_text
                if adminPassword1_text:
                    hashed_pw = bcrypt.generate_password_hash(adminPassword1_text).decode('utf-8')
                    admin.adminPassword = hashed_pw

                db.session.commit()
                flash("Successfully updated", 'success')
                return redirect(url_for('admin_profile'))


    return render_template(
        'adminPart/adminProfile.html',
        active_tab='admin_profiletab',
        admin_name=admin.adminName if admin else '',
        admin_id=admin.adminId if admin else '',
        admin_email=admin.adminEmail if admin else '',
        adminContact_text=adminContact_text,
        adminPassword1_text=adminPassword1_text,
        adminPassword2_text=adminPassword2_text,
        error_message=error_message
    )







