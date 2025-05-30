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
@app.route('/deanLogin', methods=['GET', 'POST'])
def dean_login():
    dean_login_text = ''
    dean_password_text = ''
    error_message = None

    if request.method == 'POST':
        dean_login_text = request.form.get('textbox', '').strip()
        dean_password_text = request.form.get('password', '').strip()
        valid, result = check_login('dean', dean_login_text, dean_password_text)
        if not valid:
            error_message = result
        else:
            session['dean_id'] = result  # Store the user ID in session
            return redirect(url_for('dean_homepage'))
        
    return render_template('deanPart/deanLogin.html', dean_login_text=dean_login_text, dean_password_text=dean_password_text, error_message=error_message)

# register page (done with all input validation and userID as Primary Key)
@app.route('/deanRegister', methods=['GET', 'POST'])
def dean_register():
    deanId_text = ''
    deanName_text = ''
    deanDepartment_text = ''
    deanEmail_text = ''
    deanContact_text = ' '
    deanPassword1_text = ''
    deanPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        deanId_text = request.form.get('userid', '').strip()
        deanName_text = request.form.get('username', '').strip()
        deanDepartment_text = request.form.get('department', '').strip()
        deanEmail_text = request.form.get('email', '').strip()
        deanContact_text = request.form.get('contact', '').strip()
        deanPassword1_text = request.form.get('password1', '').strip()
        deanPassword2_text = request.form.get('password2', '').strip()

        # Use the new check_register function
        is_valid, error_message = check_register(deanId_text, deanEmail_text, deanContact_text)
        if not is_valid:
            pass  # error_message is already set
        elif not all([deanId_text, deanName_text, deanDepartment_text, deanEmail_text, deanContact_text]):
            error_message = "All fields are required."
        elif not email_format(deanEmail_text):
            error_message = "Wrong Email Address format"
        elif not contact_format(deanContact_text):
            error_message = "Wrong Contact Number format"
        elif deanPassword1_text != deanPassword2_text:
            error_message = "Passwords do not match."
        elif not password_format(deanPassword1_text):
            error_message = "Wrong password format."
        else:
            hashed_pw = bcrypt.generate_password_hash(deanPassword1_text).decode('utf-8')
            new_dean = User(
                userId = deanId_text,
                userName = deanName_text.upper(),
                userDepartment = deanDepartment_text,
                userLevel = '2',
                userEmail = deanEmail_text,
                userContact = deanContact_text,
                userPassword = hashed_pw,
                userStatus = True
            )
            
            db.session.add(new_dean)
            db.session.commit()
            flash(f"Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('dean_login'))

    return render_template('deanPart/deanRegister.html', deanId_text=deanId_text, deanName_text=deanName_text, deanDepartment_text=deanDepartment_text,
                            deanEmail_text=deanEmail_text, deanPassword1_text=deanPassword1_text, deanPassword2_text=deanPassword2_text, error_message=error_message)

# forgot password page (done when the email exist in database will send reset email link)
@app.route('/deanForgotPassword', methods=['GET', 'POST'])
def dean_forgotPassword():
    dean_forgot_email_text = ''
    error_message = None

    if request.method == 'POST':
        dean_forgot_email_text = request.form.get('email', '').strip()
        if not dean_forgot_email_text:
            error_message = "Email address is required."
        else:
            success, message = check_forgotPasswordEmail('dean', dean_forgot_email_text)
            if not success:
                error_message = message
            else:
                return redirect(url_for('dean_login'))

    return render_template('deanPart/deanForgotPassword.html', dean_forgot_email_text=dean_forgot_email_text, error_message=error_message)

# reset password page (done after reset password based on that user password)
@app.route('/deanResetPassword/<token>', methods=['GET', 'POST'])
def dean_resetPassword(token):
    dean_password_text_1 = ''
    dean_password_text_2 = ''
    error_message = None
    
    if request.method == 'POST':
        dean_password_text_1 = request.form.get('password1', '').strip()
        dean_password_text_2 = request.form.get('password2', '').strip()
        
        user, error_message = check_resetPassword('dean', token, dean_password_text_1, dean_password_text_2)
        if user and not error_message:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('dean_login'))
    
    return render_template('deanPart/deanResetPassword.html', dean_password_text_1=dean_password_text_1, dean_password_text_2=dean_password_text_2, error_message=error_message)

# Logout button from homepage to login page
@app.route('/deanLogout')
def dean_logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('dean_login')) 


# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_dean_data():
    deanId = session.get('dean_id')
    if deanId:
        dean = User.query.get(deanId)
        if dean:
            return {
                'dean_id': deanId,
                'dean_name': dean.userName,
                'dean_department': dean.userDepartment,
                'dean_level': 'Dean',
                'dean_email': dean.userEmail,
                'dean_contact' : dean.userContact,
                'dean_status': dean.userStatus
            }
    return {
        'dean_id': None,
        'dean_name': '',
        'dean_department': '',
        'dean_level': '',
        'dean_email': '',
        'dean_contact': '' ,
        'dean_status': ''
    }


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/deanHome', methods=['GET', 'POST'])
def dean_homepage():
    return render_template('deanPart/deanHomepage.html', active_tab='home')