from flask import render_template, request, redirect, url_for, flash, session, g
from flask_mail import Message
from app import app, db, mail
from .backend import *
from werkzeug.security import generate_password_hash, check_password_hash
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

    if request.method == 'POST':
        login_text = request.form.get('textbox', '').strip()
        password_text = request.form.get('password', '').strip()

        valid, result = check_login(login_text, password_text)
        if not valid:
            error_message = result
        else:
            session['user_id'] = result  # Store the user ID in session
            return redirect(url_for('home_page'))

    return render_template('login_page.html', login_text=login_text,
                           password_text=password_text, error_message=error_message)


# register page (done with all input validation and userID as Primary Key)
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    userid_text = ''
    username_text = ''
    department_text = ''
    email_text = ''
    contact_text = ''
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

        # Check if any user exists with same userid, email, or contact
        user_exists = User.query.filter(
            (User.userid == userid_text) | 
            (User.email == email_text) | 
            (User.contact == contact_text)
        ).first()

        if user_exists:
            if user_exists.userid == userid_text:
                error_message = "User ID already exists."
            elif user_exists.email == email_text:
                error_message = "Email address already registered."
            elif user_exists.contact == contact_text:
                error_message = "Contact number already registered."
        elif not all([userid_text, username_text, department_text, email_text, contact_text]):
            error_message = "All fields are required."
        elif not email_format(email_text):
            error_message = "Wrong Email Address format"
        elif not contact_format(contact_text):
            error_message = "Wrong Contact Number format"
        elif not password_format(password1_text):
            error_message = "Wrong Password format"
        elif password1_text != password2_text:
            error_message = "Passwords do not match."
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
            flash("Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('login_page'))

    return render_template('register_page.html', userid_text=userid_text, username_text=username_text, 
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
            error_message = "Email address are required."
        else:
            # Check if a user with the given email exists
            user = User.query.filter_by(email=forgot_email_text).first() 

            if not user:
                error_message = "Invalid Email address."
            
            else:
                token = serializer.dumps(forgot_email_text, salt='password-reset-salt')
                reset_link = url_for('reset_password_page', token=token, _external=True)

                msg = Message('InvigilateX - Password Reset Request', recipients=[forgot_email_text])
                msg.body = f'''Hi,

                We received a request to reset your password for your InvigilateX account.

                To reset your password, please click the link below:
                {reset_link}

                If you did not request this change, please ignore this email.

                Thank you,
                The InvigilateX Team'''
                try:
                    mail.send(msg)
                    # Set the flash message
                    flash(f"Reset email sent to {forgot_email_text}!", "success")
                    return redirect(url_for('login_page'))
                except Exception as e:
                    # if unable to send email
                    flash(f"Failed to send email. Error: {str(e)}")
                    return render_template('forgotPassword_page.html', forgot_email_text=forgot_email_text, error_message=error_message)

    return render_template('forgotPassword_page.html', forgot_email_text=forgot_email_text, error_message=error_message)

# reset password page (done after reset password based on that user password)
@app.route('/resetPassword/<token>', methods=['GET', 'POST'])
def reset_password_page(token):
    password_text_1 = ''
    password_text_2 = ''
    error_message = None

    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour
    except Exception:
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for('forgot_password_page'))

    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '').strip()
        password_text_2 = request.form.get('password2', '').strip()

        if not password_text_1 or not password_text_2:
            error_message = "All fields are required."
        elif password_text_1 != password_text_2:
            error_message = "Passwords do not match."
        elif not password_format(password_text_1):
            error_message = "Wrong password format."
        else:
            hashed_pw = bcrypt.generate_password_hash(password_text_1).decode('utf-8')
            user = User.query.filter_by(email=email).first()
            if user:
                user.password = hashed_pw
                db.session.commit()
                flash("Password reset successful! Log in with your new password.", "success")
                return redirect(url_for('login_page'))
            else:
                error_message = "User not found."

    return render_template('resetPassword_page.html', error_message=error_message)


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/home', methods=['GET', 'POST'])
def home_page():
    # Now able to get the user who is login
    user_id = session.get('user_id')  # Retrieve user ID from session
    flash(f"Logged in as User ID: {user_id}")

    if user_id:
        message = f"Logged in as User ID: {user_id}"
    else:
        message = "Guest user - not logged in"
    
    return render_template('home_page.html', message=message)
