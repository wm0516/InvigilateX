from flask import render_template, request, redirect, url_for, flash, session
from app import app
from .backend import *
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

# Set the default link into admin_login, because this program have 3 login phase
@app.route('/')
def index():
    return redirect(url_for('login'))

# login page (done with checking email address and hash password)
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_text = ''
    password_text = ''

    if request.method == 'POST':
        login_text = request.form.get('textbox', '').strip()
        password_text = request.form.get('password', '').strip()
        
        if not login_text or not password_text:
            flash("Please fill in all fields", 'input_error')
            return render_template('frontPart/login.html', login_text=login_text, password_text=password_text)
        
        valid, result, role = check_login(login_text, password_text)
        if not valid:
            flash(result, 'error')
            return render_template('frontPart/login.html', login_text=login_text, password_text=password_text)

        session['user_id'] = result
        session['user_role'] = role

        if role == ADMIN:
            return redirect(url_for('admin_homepage'))
        elif role == DEAN or HOP:
            return redirect(url_for('dean_homepage'))
        elif role == LECTURER:
            return redirect(url_for('lecturer_homepage'))
        else:
            flash("Unknown role", "error")
            return redirect(url_for('login'))

    return render_template('frontPart/login.html', login_text=login_text, password_text=password_text)


# register page (done with all input validation and userID as Primary Key)
@app.route('/register', methods=['GET', 'POST'])
def register():
    id_text = ''
    name_text = ''
    email_text = ''
    contact_text = ''
    password1_text = ''
    password2_text = ''
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
        id_text = request.form.get('userid', '').strip()
        name_text = request.form.get('username', '').strip()
        email_text = request.form.get('email', '').strip()
        contact_text = request.form.get('contact', '').strip()
        password1_text = request.form.get('password1', '').strip()
        password2_text = request.form.get('password2', '').strip()
        department_text = request.form.get('department', '').strip()
        role_text = request.form.get('role', '').strip()

        is_valid, error_message = check_register(id_text, email_text, contact_text)
        
        if not is_valid:
            pass
        elif not all([id_text, name_text, email_text, contact_text, password1_text, password2_text, department_text, role_text]):
            error_message = "All fields are required."
        elif not email_format(email_text):
            error_message = "Wrong Email Address format"
        elif not contact_format(contact_text):
            error_message = "Wrong Contact Number format"
        elif password1_text != password2_text:
            error_message = "Passwords do not match."
        elif not password_format(password1_text):
            error_message = "Wrong password format."
        elif role_text not in role_map:
            error_message = "Invalid role selected."

        if error_message:
            flash(error_message, 'error')
        else:
            hashed_pw = bcrypt.generate_password_hash(password1_text).decode('utf-8')
            new_user = User(
                userId=id_text,
                userName=name_text.upper(),
                userDepartment=department_text.upper(),
                userLevel=role_map[role_text],  # use mapped constant
                userEmail=email_text,
                userContact=contact_text,
                userPassword=hashed_pw,
                userStatus=False
            )

            db.session.add(new_user)
            db.session.commit()
            flash("Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('login'))

    return render_template('frontPart/register.html',
                           id_text=id_text,
                           name_text=name_text,
                           email_text=email_text,
                           contact_text=contact_text,
                           password1_text=password1_text,
                           password2_text=password2_text,
                           department_text=department_text,
                           role_text=role_text,
                           error_message=error_message)


# forgot password page (done when the email exist in database will send reset email link)
@app.route('/forgotPassword', methods=['GET', 'POST'])
def forgotPassword():
    forgot_email_text = ''
    error_message = None

    if request.method == 'POST':
        forgot_email_text = request.form.get('email', '').strip()

        # Validate and send reset email
        success, message = check_forgotPasswordEmail(forgot_email_text)
        if not success:
            error_message = message
            flash(str(error_message), 'error')
        else:
            flash("Reset link sent to your email address.", 'success')
            return redirect(url_for('login'))

    return render_template('frontPart/forgotPassword.html', forgot_email_text=forgot_email_text, error_message=error_message)


# reset password page (done after reset password based on that user password)
@app.route('/resetPassword/<token>', methods=['GET', 'POST'])
def resetPassword(token):
    password_text_1 = ''
    password_text_2 = ''
    error_message = None

    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '').strip()
        password_text_2 = request.form.get('password2', '').strip()

        user, error_message = check_resetPassword(token, password_text_1, password_text_2)
        if error_message:
            flash(error_message, 'error')
        elif user:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('login'))

    return render_template('frontPart/resetPassword.html', 
                           password_text_1=password_text_1, 
                           password_text_2=password_text_2, 
                           error_message=error_message)


# Logout button from homepage to login page
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login')) 

# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_user_data():
    userId = session.get('user_id')
    if userId:
        user = User.query.get(userId)
        if user:
            return {
                'user_id': userId,
                'user_name': user.userName,
                'user_department': user.userDepartment,
                'user_level': user.userLevel,
                'user_email': user.userEmail,
                'user_contact': user.userContact,
                'user_password': user.userPassword,
                'user_status': user.userStatus
            }
    return {
        'user_id': None,
        'user_name': '',
        'user_department': '',
        'user_level': '',
        'user_email': '',
        'user_contact': '',
        'user_password': '',
        'user_status': ''
    }


# admin homepage
@app.route('/adminHome', methods=['GET', 'POST'])
def admin_homepage():
    return render_template('adminPart/adminHomepage.html', active_tab='admin_hometab')


# dean&hop homepage
@app.route('/deanHome', methods=['GET', 'POST'])
def dean_homepage():
    return render_template('deanPart/deanHomepage.html', active_tab='home')


# lecturer homepage
@app.route('/lecturerHome', methods=['GET', 'POST'])
def lecturer_homepage():
    return render_template('lecturerPart/lecturerHomepage.html', active_tab='lecturer_hometab')












