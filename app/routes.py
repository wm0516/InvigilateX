from flask import render_template, request, redirect, url_for, flash, session
from app import app, db
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


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/home', methods=['GET', 'POST'])
def homepage():
    # Retrieve user ID from session
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_name = ''
    user_department = ''

    if user_id:
        # Query the user from the database
        user = User.query.get(user_id)
        if user:
            user_name = user.username
            user_department = user.department   
            # flash(f"(flash){user} Logged in as User ID: {user_id}, User Name: {user.username}" )
        else:
            pass

    return render_template('mainPart/homepage.html', user_id = user_id, user_name=user_name, user_department=user_department, active_tab='home')

# Logout button from homepage to login page
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login_page'))  # Make sure you have a 'login_page' route

@app.route('/home/autoGenerate')
def auto_generate():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_name = ''
    user_department = ''

    if user_id:
        # Query the user from the database
        user = User.query.get(user_id)
        if user:
            user_name = user.username
            user_department = user.department   
            # flash(f"(flash){user} Logged in as User ID: {user_id}, User Name: {user.username}" )
        else:
            pass

    return render_template('mainPart/generateSchedule.html', user_id = user_id, user_name=user_name, user_department=user_department, active_tab='autoGenerate')

@app.route('/home/manageLecturer')
def manage_lecturer():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_name = ''
    user_department = ''

    if user_id:
        # Query the user from the database
        user = User.query.get(user_id)
        if user:
            user_name = user.username
            user_department = user.department   
            # flash(f"(flash){user} Logged in as User ID: {user_id}, User Name: {user.username}" )
        else:
            pass

    return render_template('mainPart/manageLecturer.html', user_id = user_id, user_name=user_name, user_department=user_department, active_tab='manage')


@app.route('/home/uploadLecturerTimetable')
def upload_lecturer_timetable():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_name = ''
    user_department = ''

    if user_id:
        # Query the user from the database
        user = User.query.get(user_id)
        if user:
            user_name = user.username
            user_department = user.department   
            # flash(f"(flash){user} Logged in as User ID: {user_id}, User Name: {user.username}" )
        else:
            pass

    return render_template('mainPart/uploadLecturerTimetable.html', user_id = user_id, user_name=user_name, user_department=user_department, active_tab='uploadLecturerTimetable')

@app.route('/home/uploadExamDetails')
def upload_exam_details():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_name = ''
    user_department = ''

    if user_id:
        # Query the user from the database
        user = User.query.get(user_id)
        if user:
            user_name = user.username
            user_department = user.department   
            # flash(f"(flash){user} Logged in as User ID: {user_id}, User Name: {user.username}" )
        else:
            pass

    return render_template('mainPart/uploadExamDetails.html', user_id = user_id, user_name=user_name, user_department=user_department, active_tab='uploadExamDetails')

@app.route('/home/upload')
def upload():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_name = ''
    user_department = ''

    if user_id:
        # Query the user from the database
        user = User.query.get(user_id)
        if user:
            user_name = user.username
            user_department = user.department   
            # flash(f"(flash){user} Logged in as User ID: {user_id}, User Name: {user.username}" )
        else:
            pass

    return render_template('mainPart/upload.html', user_id = user_id, user_name=user_name, user_department=user_department, active_tab='upload')

