from flask import render_template, request, redirect, url_for, flash, session, get_flashed_messages
from app import app
from .backend import *
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()




# -------------------------------
# Function for default route 
# -------------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))


# -------------------------------
# Function for Auth Login route
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_text = ''
    password_text = ''

    if request.method == 'POST':
        login_text = request.form.get('login_field', '').strip()
        password_text = request.form.get('password_field', '').strip()
        
        valid, result, role = check_login(login_text, password_text)
        if not valid:
            flash(result, 'login_error')
            all_messages = get_flashed_messages(with_categories=True)
            return render_template('auth/login.html', login_text=login_text, password_text=password_text, all_messages=all_messages)

        session['user_id'] = result
        session['user_role'] = role

        if role == ADMIN:
            return redirect(url_for('admin_homepage'))
        elif role == DEAN:
            return redirect(url_for('dean_homepage'))
        elif role == HOP:
            return redirect(url_for('hop_homepage'))
        elif role == LECTURER:
            return redirect(url_for('lecturer_homepage'))
        else:
            flash("Unknown role", "login_error")
            return redirect(url_for('login'))

    # Ensure GET request also includes flashed messages
    all_messages = get_flashed_messages(with_categories=True)
    return render_template('auth/login.html', login_text=login_text, password_text=password_text, all_messages=all_messages)


# -------------------------------
# Function for Auth Register route
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    role_map = {
        'LECTURER': LECTURER,
        'DEAN': DEAN,
        'HOP': HOP,
        'ADMIN': ADMIN
    }
    
    department_data = Department.query.all()
    id_text = ''
    name_text = ''
    email_text = ''
    contact_text = ''
    department_text = ''
    role_text = ''
    gender_text = ''
    password1_text = ''
    password2_text = ''
    error_message = None

    if request.method == 'POST':
        id_text = request.form.get('userid', '').strip()
        name_text = request.form.get('username', '').strip()
        email_text = request.form.get('email', '').strip()
        contact_text = request.form.get('contact', '').strip()
        department_text = request.form.get('department', '').strip()
        role_text = request.form.get('role', '').strip()
        gender_text = request.form.get('gender', '').strip()
        password1_text = request.form.get('password1', '').strip()
        password2_text = request.form.get('password2', '').strip()

        is_valid, error_message = check_register(id_text, email_text, contact_text, password1_text, password2_text)
        if error_message:
            flash(error_message, 'error')
        elif is_valid:
            hashed_pw = bcrypt.generate_password_hash(password1_text).decode('utf-8')
            new_user = User(
                userId=id_text.upper(),
                userName=name_text.upper(),
                userDepartment=department_text.upper(),
                userLevel=role_map[role_text],  # use mapped constant
                userEmail=email_text,
                userContact=contact_text,
                userPassword=hashed_pw,
                userGender=gender_text,
                userStatus=0,
                userRegisterDateTime=datetime.now()
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('login'))

    return render_template('auth/register.html', id_text=id_text, name_text=name_text, email_text=email_text,
                           contact_text=contact_text, password1_text=password1_text, password2_text=password2_text, gender_text=gender_text,
                           department_text=department_text, role_text=role_text, department_data=department_data, error_message=error_message)


# -------------------------------
# Function for Auth ForgotPassword route
# -------------------------------
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

    return render_template('auth/forgotPassword.html', forgot_email_text=forgot_email_text, error_message=error_message)


# -------------------------------
# Function for Auth ResetPassword route
# -------------------------------
@app.route('/resetPassword/<token>', methods=['GET', 'POST'])
def resetPassword(token):
    password_text_1 = ''
    password_text_2 = ''
    error_message = role_required

    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '').strip()
        password_text_2 = request.form.get('password2', '').strip()

        user, error_message = check_resetPassword(token, password_text_1, password_text_2)
        if error_message:
            flash(error_message, 'error')
        elif user:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('login'))

    return render_template('auth/resetPassword.html', password_text_1=password_text_1, password_text_2=password_text_2, error_message=error_message)


# -------------------------------
# Function for Auth Logout route
# -------------------------------
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login')) 


# -------------------------------
# Function for Auth SaveLoginCredentials 
# -------------------------------
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


# -------------------------------
# Function for Auth RequiredLoginForEachPage
# -------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------
# Function for Admin Homepage route
# -------------------------------
@app.route('/admin/home', methods=['GET', 'POST'])
@login_required
def admin_homepage():
    return render_template('admin/adminHomepage.html', active_tab='admin_hometab')


# -------------------------------
# Function for Dean Homepage route
# -------------------------------
@app.route('/dean/home', methods=['GET', 'POST'])
@login_required
def dean_homepage():
    return render_template('dean/deanHomepage.html', active_tab='dean_hometab')


# -------------------------------
# Function for HOP Homepage route
# -------------------------------
@app.route('/hop/home', methods=['GET', 'POST'])
@login_required
def hop_homepage():
    return render_template('hop/hopHomepage.html', active_tab='hop_hometab')


# -------------------------------
# Function for Lecturer Homepage route
# -------------------------------
@app.route('/lecturer/home', methods=['GET', 'POST'])
@login_required
def lecturer_homepage():
    return render_template('lecturer/lecturerHomepage.html', active_tab='lecturer_hometab')












