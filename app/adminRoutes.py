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


# login page (done with checking email address and hash password)
@app.route('/adminLogin', methods=['GET', 'POST'])
def admin_login():
    login_text = ''
    password_text = ''
    error_message = None

    # Need Uncommand back 
    '''
    if request.method == 'POST':
        login_text = request.form.get('textbox', '').strip()
        password_text = request.form.get('password', '').strip()

        valid, result = check_login(login_text, password_text)
        if not valid:
            error_message = result
        else:
            session['user_id'] = result  # Store the user ID in session
            return redirect(url_for('admin_homepage'))
    '''
    if request.method == 'POST':
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
    return render_template('adminPart/adminHomepage.html', active_tab='home')

@app.route('/home/autoGenerate', methods=['GET', 'POST'])
def admin_autoGenerate():
    if request.method == 'POST':
        flash(f"{request.method}")
        flash(f"{request.files}")
        flash(f"{request.form}")
    return render_template('adminPart/adminAutoSchedule.html', active_tab='autoGenerate')

@app.route('/adminHome/manageLecturer')
def admin_manageLecturer():
    return render_template('adminPart/adminManageLecturer.html', active_tab='manage')

@app.route('/adminHome/upload')
def admin_upload():
    return render_template('adminPart/adminUpload.html', active_tab='upload')







UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/adminHome/uploadLecturerTimetable', methods=['GET', 'POST'])
def admin_uploadLecturerTimetable():
    if request.method == 'POST':
        #flash(f"{request.method}")
        #flash(f"{request.files}")
        #flash(f"{request.form}")

        if 'lecturer_file' not in request.files:
            flash('No file part')
            return jsonify({'error': 'No file part in the request'}), 400

        file = request.files['lecturer_file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file.filename is None:
            return jsonify({'error': 'Filename is missing.'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            return jsonify({
                'message': 'Lecturer timetable file uploaded and read successfully!',
                'columns': df.columns.tolist(),
                'preview': df.head(3).to_dict(orient='records')
            })
        except Exception as e:
            return jsonify({'error': f'Failed to read Excel file: {str(e)}'}), 500

    return render_template('adminPart/adminUploadLecturerTimetable.html', active_tab='uploadLecturerTimetable')









@app.route('/adminHome/uploadExamDetails', methods=['GET', 'POST'])
def admin_uploadExamDetails():
    if request.method == 'POST':

        if 'exam_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})

        file = request.files['exam_file']
        file_stream = BytesIO(file.read())
        records_added = 0
        errors = []
        warnings = []

        try:
            excel_file = pd.ExcelFile(file_stream)
            
            for sheet_name in excel_file.sheet_names:
                current_app.logger.info(f"Processing sheet: {sheet_name}")

                try:
                    # ✅ Only reads columns A to I, skips the first row (headers start from row 2)
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        usecols="A:I",
                        skiprows=1
                    )

                    # ✅ Assign expected column names
                    df.columns = ['Date', 'Day', 'Start', 'End', 'Program', 'Course/Sec', 'Lecturer', 'No Of', 'Room']

                    # ➕ You can add further logic to insert or process the data here.
                    records_added += len(df)

                except Exception as e:
                    error_msg = f"Error processing sheet '{sheet_name}': {str(e)}"
                    errors.append(error_msg)
                    current_app.logger.error(error_msg)
                    continue

            response_data = {
                'success': True,
                'message': f'Successfully processed {records_added} record(s).'
            }

            if warnings:
                response_data['warnings'] = warnings
            if errors:
                response_data['errors'] = errors

            return jsonify(response_data)

        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            current_app.logger.error(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            })
        
    return render_template('adminPart/adminUploadExamDetails.html', active_tab='uploadExamDetails')

        



'''
@app.route('/home/uploadExamDetails', methods=['GET', 'POST'])
def upload_exam_details():
    exam_data = ''
    if request.method == 'POST':
        #flash(f"{request.method}")
        #flash(f"{request.files}")
        #flash(f"{request.form}")
        #flash(f"Files keys: {list(request.files.keys())}")
        if 'exam_file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        file = request.files['exam_file']
        try:
            excel_file = pd.ExcelFile(file)

            for sheet_name in excel_file.sheet_names:
                current_app.logger.info(f"Processing sheet: {sheet_name}")
                department_code = sheet_name.strip().upper()
            pass
        except:
            pass

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file.filename is None:
            return jsonify({'error': 'Filename is missing.'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            return jsonify({
                'message': 'File uploaded and read successfully!',
                'columns': df.columns.tolist(),
                'preview': df.head(3).to_dict(orient='records')
            })
        except Exception as e:
            return jsonify({'error': f'Failed to read Excel file: {str(e)}'}), 500
        
    return render_template('mainPart/uploadExamDetails.html', active_tab='uploadExamDetails', exam_data=exam_data)


























@app.route('/home/uploadExamDetails', methods=['GET', 'POST'])
def upload_exam_details():
    exam_data=''
    if request.method == 'POST':
        flash(f"{request.method}")
        flash(f"{request.files}")
        flash(f"{request.form}")
        flash(f"Files keys: {list(request.files.keys())}")
        if 'exam_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['exam_file']
        
        if not file or not file.filename:
            flash('No file selected')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                df = pd.read_excel(filepath)  # Use pd.read_csv() if using .csv files
                exam_data = df.to_dict(orient='records')  # Converts DataFrame to a list of dicts

                print(df.head())  # Debugging
                return "File uploaded and read successfully!"
            except Exception as e:
                flash(f"Error reading Excel file: {e}")
                return redirect(request.url)

        flash('Invalid file type. Only Excel files are supported.')
        return redirect(request.url)

    return render_template('mainPart/uploadExamDetails.html', active_tab='uploadExamDetails', exam_data=exam_data)
'''


'''
if 'exam_file' not in request.files:
    return redirect(request.url)

file = request.files['exam_file']

try:
    excel_file = pd.ExcelFile(file)

    for sheet_name in excel_file.sheet_names:
        current_app.logger.info(f"Processing sheet: {sheet_name}")
        # department_code = sheet_name.strip().upper()

        try:
            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
                usecold="A:c"
            )

            df.columns = ['Name', 'Email', 'Level']

        except:
            pass

except:
    pass
'''