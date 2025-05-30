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
@app.route('/lecturerLogin', methods=['GET', 'POST'])
def lecturer_login():
    lecturer_login_text = ''
    lecturer_password_text = ''
    error_message = None

    if request.method == 'POST':
        lecturer_login_text = request.form.get('textbox', '').strip()
        lecturer_password_text = request.form.get('password', '').strip()
        valid, result = check_login('lecturer', lecturer_login_text, lecturer_password_text)
        if not valid:
            error_message = result
        else:
            session['lecturer_id'] = result  # Store the user ID in session
            return redirect(url_for('lecturer_homepage'))

    return render_template('lecturerPart/lecturerLogin.html', lecturer_login_text=lecturer_login_text, lecturer_password_text=lecturer_password_text, error_message=error_message)

# register page (done with all input validation and userID as Primary Key)
@app.route('/lecturerRegister', methods=['GET', 'POST'])
def lecturer_register():
    lecturerId_text = ''
    lecturerName_text = ''
    lecturerDepartment_text = ''
    lecturerEmail_text = ''
    lecturerContact_text = ' '
    lecturerPassword1_text = ''
    lecturerPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        lecturerId_text = request.form.get('userid', '').strip()
        lecturerName_text = request.form.get('username', '').strip()
        lecturerDepartment_text = request.form.get('department', '').strip()
        lecturerEmail_text = request.form.get('email', '').strip()
        lecturerContact_text = request.form.get('contact', '').strip()
        lecturerPassword1_text = request.form.get('password1', '').strip()
        lecturerPassword2_text = request.form.get('password2', '').strip()

        # Use the new check_register function
        is_valid, error_message = check_register(lecturerId_text, lecturerEmail_text, lecturerContact_text)
        if not is_valid:
            pass  # error_message is already set
        elif not all([lecturerId_text, lecturerName_text, lecturerDepartment_text, lecturerEmail_text, lecturerContact_text]):
            error_message = "All fields are required."
        elif not email_format(lecturerEmail_text):
            error_message = "Wrong Email Address format"
        elif not contact_format(lecturerContact_text):
            error_message = "Wrong Contact Number format"
        elif lecturerPassword1_text != lecturerPassword2_text:
            error_message = "Passwords do not match."
        elif not password_format(lecturerPassword1_text):
            error_message = "Wrong password format."
        else:
            hashed_pw = bcrypt.generate_password_hash(lecturerPassword1_text).decode('utf-8')
            new_lecturer = User(
                userId = lecturerId_text,
                userName = lecturerName_text.upper(),
                userDepartment = lecturerDepartment_text,
                userLevel = '1',
                userEmail = lecturerEmail_text,
                userContact = lecturerContact_text,
                userPassword = hashed_pw,
                userStatus = True
            )
            db.session.add(new_lecturer)
            db.session.commit()
            flash(f"Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('lecturer_login'))

    return render_template('lecturerPart/lecturerRegister.html', lecturerId_text=lecturerId_text, lecturerName_text=lecturerName_text, 
                           lecturerDepartment_text=lecturerDepartment_text, lecturerEmail_text=lecturerEmail_text, lecturerContact_text=lecturerContact_text, 
                           lecturerPassword1_text=lecturerPassword1_text, lecturerPassword2_text=lecturerPassword2_text, error_message=error_message)

# forgot password page (done when the email exist in database will send reset email link)
@app.route('/lecturerForgotPassword', methods=['GET', 'POST'])
def lecturer_forgotPassword():
    lecturer_forgot_email_text = ''
    error_message = None

    if request.method == 'POST':
        lecturer_forgot_email_text = request.form.get('email', '').strip()
        if not lecturer_forgot_email_text:
            error_message = "Email address is required."
        else:
            success, message = check_forgotPasswordEmail('lecturer', lecturer_forgot_email_text)
            if not success:
                error_message = message
            else:
                return redirect(url_for('lecturer_login'))

    return render_template('lecturerPart/lecturerForgotPassword.html', 
                         lecturer_forgot_email_text=lecturer_forgot_email_text, 
                         error_message=error_message)

# reset password page (done after reset password based on that user password)
@app.route('/lecturerResetPassword/<token>', methods=['GET', 'POST'])
def lecturer_resetPassword(token):
    lecturer_password_text_1 = ''
    lecturer_password_text_2 = ''
    error_message = None
    
    if request.method == 'POST':
        lecturer_password_text_1 = request.form.get('password1', '').strip()
        lecturer_password_text_2 = request.form.get('password2', '').strip()
        
        user, error_message = check_resetPassword('lecturer', token, lecturer_password_text_1, lecturer_password_text_2)
        if user and not error_message:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('lecturer_login'))
    
    return render_template('lecturerPart/lecturerResetPassword.html', lecturer_password_text_1=lecturer_password_text_1, 
                           lecturer_password_text_2=lecturer_password_text_2, error_message=error_message)

# Logout button from homepage to login page
@app.route('/lecturerLogout')
def lecturer_logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('lecturer_login')) 


# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_lecturer_data():
    lecturerId = session.get('lecturer_id')
    if lecturerId:
        lecturer = User.query.get(lecturerId)
        if lecturer:
            return {
                'lecturer_id': lecturerId,
                'lecturer_name': lecturer.userName,
                'lecturer_department': lecturer.userDepartment,
                'lecturer_level': lecturer.userLevel,
                'lecturer_email': lecturer.userEmail,
                'lecturer_contact' : lecturer.userContact,
                'lecturer_status': lecturer.userStatus
            }
    return {
        'lecturer_id': None,
        'lecturer_name': '',
        'lecturer_department': '',
        'lecturer_level': '',
        'lecturer_email': '',
        'lecturer_contact': '',
        'lecturer_status': ''
    }



# home page (start with this!!!!!!!!!!!!!!)
@app.route('/lecturerHome', methods=['GET', 'POST'])
def lecturer_homepage():
    return render_template('lecturerPart/lecturerHomepage.html', active_tab='home')
