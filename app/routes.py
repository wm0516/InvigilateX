from flask import render_template, request, redirect, url_for, flash
from flask_mail import Message
from app import app, db, mail
from .backend import *
from werkzeug.security import generate_password_hash, check_password_hash
from .database import *

@app.route('/', methods=['GET', 'POST'])
def login_page():
    login_text = ''
    password_text = ''
    error_message = None

    if request.method == 'POST':
        login_text = request.form.get('textbox', '')
        password_text = request.form.get('password', '')

        # Check if a user with the given email exists
        user = User.query.filter_by(email=login_text).first()

        if not login_text or not password_text:
            error_message = "Both fields are required."
        elif not user or not check_password_hash(user.password, password_text):
            error_message = "Invalid Email address or password."
        else:
            # Successful login
            return redirect(url_for('home_page'))

    return render_template('login_page.html', login_text=login_text,
                           password_text=password_text, error_message=error_message)



# register page (done)
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
        password1_text = request.form.get('password1', '')
        password2_text = request.form.get('password2', '')

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
            hashed_pw = generate_password_hash(password1_text)
            new_user = User(
                userid=userid_text,
                username=username_text.upper(),
                department=department_text,
                email=email_text,
                contact=contact_text,
                password=hashed_pw
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('login_page'))

    return render_template('register_page.html', userid_text=userid_text, username_text=username_text, 
                           email_text=email_text, contact_text=contact_text, password1_text=password1_text, 
                           password2_text=password2_text, error_message=error_message)



@app.route('/home')
def home_page():
    return render_template('home_page.html')


@app.route('/forgotPassword', methods=['GET', 'POST'])
def forgot_password_page():
    forgot_email_text = ''
    error_message = None
    if request.method == 'POST':
        forgot_email_text = request.form.get('email', '')

        if not forgot_email_text:
            error_message = "Field can't be empty."
        # change it to check with database
        # elif not email_format(forgot_email_text):
        #   error_message = "Wrong Email Address format"
        else:
            reset_link = url_for('reset_password_page', _external=True)
            msg = Message('Reset Your Password', recipients=[forgot_email_text])
            msg.body = f'Click the link to reset your password: {reset_link}'
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


@app.route('/resetPassword', methods=['GET', 'POST'])
def reset_password_page():
    password_text_1 = ''
    password_text_2 = ''
    error_message = None
    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '')
        password_text_2 = request.form.get('password2', '')

        if password_text_1 != password_text_2:
            error_message = "Passwords do not match."
        elif not all([password_text_1, password_text_2]):
            error_message = "All fields are required."
        elif not password_format(password_text_1):
            error_message = "Wrong Password format"
        else:
            # Update logic for user's password
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('login_page'))

    return render_template('resetPassword_page.html', password_text_1=password_text_1,
                           password_text_2=password_text_2, error_message=error_message)
