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

@app.route('/')
def index():
    return redirect(url_for('admin_login'))

# login page (done with checking email address and hash password)
@app.route('/adminLogin', methods=['GET', 'POST'])
def admin_login():
    login_text = ''
    password_text = ''
    error_message = None

    # Need Uncommand back 
    if request.method == 'POST':
        login_text = request.form.get('textbox', '').strip()
        password_text = request.form.get('password', '').strip()

        valid, result = check_login(login_text, password_text)
        if not valid:
            error_message = result
        else:
            session['user_id'] = result  # Store the user ID in session
            return redirect(url_for('admin_homepage'))

    return render_template('adminPart/adminLogin.html', login_text=login_text, password_text=password_text, error_message=error_message)

# register page (done with all input validation and userID as Primary Key)
@app.route('/adminRegister', methods=['GET', 'POST'])
def admin_register():
    userid_text = ''
    username_text = ''
    department_text = ''
    email_text = ''
    contact_text = ' '
    password1_text = ''
    password2_text = ''
    error_message = None

    if request.method == 'POST':
        userid_text = request.form.get('userid', '').strip()
        username_text = request.form.get('username', '').strip()
        department_text = request.form.get('department', '').strip()
        email_text = request.form.get('email', '').strip()
        contact_text = request.form.get('contact', '').strip()
        password1_text = request.form.get('password1', '').strip()
        password2_text = request.form.get('password2', '').strip()

        # Use the new check_register function
        is_valid, error_message = check_register(userid_text, email_text, contact_text)
        
        if not is_valid:
            pass  # error_message is already set
        elif not all([userid_text, username_text, department_text, email_text, contact_text]):
            error_message = "All fields are required."
        elif not email_format(email_text):
            error_message = "Wrong Email Address format"
        elif not contact_format(contact_text):
            error_message = "Wrong Contact Number format"
        elif password1_text != password2_text:
            error_message = "Passwords do not match."
        elif not password_format(password1_text):
            error_message = "Wrong password format."
        else:
            hashed_pw = bcrypt.generate_password_hash(password1_text).decode('utf-8')
            new_user = User(
                userid = userid_text,
                username = username_text.upper(),
                department = department_text,
                email = email_text,
                contact = contact_text,
                password = hashed_pw
            )
            
            db.session.add(new_user)
            db.session.commit()
            flash(f"Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('admin_login'))

    return render_template('adminPart/adminRegister.html', userid_text=userid_text, username_text=username_text, 
                           email_text=email_text, contact_text=contact_text, password1_text=password1_text, 
                           password2_text=password2_text, error_message=error_message)

# forgot password page (done when the email exist in database will send reset email link)
@app.route('/adminForgotPassword', methods=['GET', 'POST'])
def admin_forgotPassword():
    forgot_email_text = ''
    error_message = None

    if request.method == 'POST':
        forgot_email_text = request.form.get('email', '').strip()

        if not forgot_email_text:
            error_message = "Email address is required."
        else:
            success, message = check_forgotPasswordEmail(forgot_email_text)
            if not success:
                error_message = message
            else:
                return redirect(url_for('admin_login'))

    return render_template('adminPart/adminForgotPassword.html', 
                         forgot_email_text=forgot_email_text, 
                         error_message=error_message)

# reset password page (done after reset password based on that user password)
@app.route('/adminResetPassword/<token>', methods=['GET', 'POST'])
def admin_resetPassword(token):
    error_message = None
    
    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '').strip()
        password_text_2 = request.form.get('password2', '').strip()
        
        user, error_message = check_resetPassword(
            token, 
            password_text_1, 
            password_text_2
        )
        
        if user and not error_message:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('admin_login'))
    
    return render_template('adminPart/adminResetPassword.html', error_message=error_message)

# Logout button from homepage to login page
@app.route('/adminLogout')
def admin_logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('admin_login')) 









# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_user_data():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return {
                'user_id': user_id,
                'user_name': user.username,
                'user_department': user.department,
                'user_email': user.email,
                'user_contact': user.contact
            }
    return {
        'user_id': None,
        'user_name': '',
        'user_department': '',
        'user_email': '',
        'user_contact': ''
    }


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/adminHome', methods=['GET', 'POST'])
def admin_homepage():
    return render_template('adminPart/adminHomepage.html', active_tab='admin_hometab')

@app.route('/home/autoGenerate', methods=['GET', 'POST'])
def admin_autoGenerate():
    if request.method == 'POST':
        flash(f"{request.method}")
        flash(f"{request.files}")
        flash(f"{request.form}")
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
        if 'lecturer_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['lecturer_file']
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
                        usecols="A:E",
                        skiprows=1
                    )
                    df.columns = ['ID', 'Name', 'Department', 'Email', 'Contact']
                    df.reset_index(drop=True, inplace=True)

                    for index, row in df.iterrows():
                        try:
                            lecturer_id = str(row['ID'])
                            lecturer_name = str(row['Name'])
                            lecturer_department = str(row['Department'])
                            lecturer_email = str(row['Email'])
                            lecturer_contact = int(row['Contact'])
                            
                            is_valid, error_message = unique_LecturerDetails(
                                lecturer_id, lecturer_email, lecturer_contact
                            )

                            if not is_valid:
                                row_number = index + 2 if isinstance(index, int) else str(index)
                                errors.append(f"Row {row_number} in sheet '{sheet_name}' error: {error_message}")
                                continue
                            
                            lecturer = LecturerDetails(
                                lecturerID = lecturer_id,
                                lecturerName = lecturer_name,
                                lecturerDepartment = lecturer_department,
                                lecturerEmail = lecturer_email,
                                lecturerContact = lecturer_contact
                            )

                            db.session.add(lecturer)
                            lecturer_records_added += 1

                            processed_records.append({
                                'ID': lecturer.lecturerID,
                                'Name': lecturer.lecturerName,
                                'Department': lecturer.lecturerDepartment,
                                'Email': lecturer.lecturerEmail,
                                'Contact': lecturer.lecturerContact
                            })

                        except Exception as row_err:
                            pass

                    db.session.commit()

                except Exception as sheet_err:
                    pass
            # Final response
            if lecturer_records_added > 0:
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
            current_app.logger.error(f"File processing error: {str(e)}")
            return jsonify({'success': False, 'message': f"Error processing file: {str(e)}"})
        
    lecturer_data = LecturerDetails.query.all()
    return render_template('adminPart/adminUploadLecturerTimetable.html', active_tab='admin_uploadLecturerTimetabletab', lecturer_data=lecturer_data)


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
            if exam_records_added > 0:
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
            current_app.logger.error(f"File processing error: {str(e)}")
            return jsonify({'success': False, 'message': f"Error processing file: {str(e)}"})

    # GET request
    exam_data = ExamDetails.query.all()
    return render_template('adminPart/adminUploadExamDetails.html', active_tab='admin_uploadExamDetailstab', exam_data=exam_data)