from flask import render_template, request, redirect, url_for, flash, session
from app import app
import os
import pandas as pd
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from .backend import *
from .database import *
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()



# login page (done with checking email address and hash password)
@app.route('/', methods=['GET', 'POST'])
def login_page():
    login_text = ''
    password_text = ''
    error_message = None

    # For debug
    '''if request.method == 'POST':
        return redirect(url_for('homepage'))'''   
     
    # Need Uncommand back 
    if request.method == 'POST':
        login_text = request.form.get('textbox', '').strip()
        password_text = request.form.get('password', '').strip()

        valid, result = check_login(login_text, password_text)
        if not valid:
            error_message = result
        else:
            session['user_id'] = result  # Store the user ID in session
            return redirect(url_for('homepage'))
    

    return render_template('frontPart/login.html', login_text=login_text, 
                           password_text=password_text, error_message=error_message)

# register page (done with all input validation and userID as Primary Key)
@app.route('/register', methods=['GET', 'POST'])
def register_page():
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
            return redirect(url_for('login_page'))

    return render_template('frontPart/register.html', userid_text=userid_text, username_text=username_text, 
                           email_text=email_text, contact_text=contact_text, password1_text=password1_text, 
                           password2_text=password2_text, error_message=error_message)

# forgot password page (done when the email exist in database will send reset email link)
@app.route('/forgotPassword', methods=['GET', 'POST'])
def forgot_password_page():
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
                return redirect(url_for('login_page'))

    return render_template('frontPart/forgotPassword.html', 
                         forgot_email_text=forgot_email_text, 
                         error_message=error_message)

# reset password page (done after reset password based on that user password)
@app.route('/resetPassword/<token>', methods=['GET', 'POST'])
def reset_password_page(token):
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
            return redirect(url_for('login_page'))
    
    return render_template('frontPart/resetPassword.html', error_message=error_message)

# Logout button from homepage to login page
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login_page'))  # Make sure you have a 'login_page' route




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
@app.route('/home', methods=['GET', 'POST'])
def homepage():
    return render_template('mainPart/homepage.html', active_tab='home')

@app.route('/home/autoGenerate')
def auto_generate():
    return render_template('mainPart/generateSchedule.html', active_tab='autoGenerate')

@app.route('/home/manageLecturer')
def manage_lecturer():
    return render_template('mainPart/manageLecturer.html', active_tab='manage')

@app.route('/home/uploadLecturerTimetable')
def upload_lecturer_timetable():
    return render_template('mainPart/uploadLecturerTimetable.html', active_tab='uploadLecturerTimetable')

@app.route('/home/upload')
def upload():
    return render_template('mainPart/upload.html', active_tab='upload')




# Configurations
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'xlsm'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE
)

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if the filename has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_exam_data(df):
    """Validate the structure of the uploaded exam data"""
    required_columns = {'Date', 'Day', 'Start', 'End', 'Program', 
                       'Course/Sec', 'Lecturer', 'No Of', 'Room'}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")
    return True

@app.route('/home/uploadExamDetails', methods=['GET', 'POST'])
def upload_exam_details():
    exam_data = []
    if request.method == 'POST':
        try:
            # Debugging info
            app.logger.debug(f"Request files: {request.files}")
            
            # Check if file was uploaded
            if 'exam_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(request.url)
            
            file = request.files['exam_file']
            
            # Check if file was selected and has a filename
            if not file or not file.filename:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            # Ensure filename is a string (not None)
            filename = file.filename if file.filename else ''
            if not filename:
                flash('Invalid filename', 'error')
                return redirect(request.url)
            
            # Validate file type
            if not allowed_file(filename):
                flash('Invalid file type. Only Excel files (.xlsx, .xls, .xlsm) are supported.', 'error')
                return redirect(request.url)
            
            # Secure filename and save
            secure_name = secure_filename(filename)  # Now guaranteed to be str
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
            file.save(filepath)
            app.logger.info(f"File saved to: {filepath}")
            
            # Read and validate Excel file
            try:
                df = pd.read_excel(filepath)
                validate_exam_data(df)
                exam_data = df.to_dict(orient='records')
                app.logger.info("Data loaded successfully")
                
                # Clean up - remove the uploaded file after processing
                try:
                    os.remove(filepath)
                    app.logger.info(f"Temporary file removed: {filepath}")
                except Exception as e:
                    app.logger.error(f"Error removing temporary file: {e}")
                
                flash('File uploaded and processed successfully!', 'success')
                return render_template('mainPart/uploadExamDetails.html', 
                                    active_tab='uploadExamDetails', 
                                    exam_data=exam_data)
            
            except ValueError as ve:
                flash(f'Invalid file format: {str(ve)}', 'error')
                app.logger.error(f"Validation error: {ve}")
            except Exception as e:
                flash(f'Error reading Excel file: {str(e)}', 'error')
                app.logger.error(f"Excel read error: {e}")
            
            # Remove file if there was an error processing it
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                app.logger.error(f"Error cleaning up file: {e}")
            
            return redirect(request.url)
        
        except RequestEntityTooLarge:
            flash('File too large. Maximum size is 16MB.', 'error')
            app.logger.warning("File size exceeded limit")
            return redirect(request.url)
        
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            app.logger.error(f"Unexpected error: {e}")
            return redirect(request.url)

    # GET request
    return render_template('mainPart/uploadExamDetails.html', 
                         active_tab='uploadExamDetails', 
                         exam_data=exam_data)