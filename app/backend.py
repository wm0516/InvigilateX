import re
from flask_bcrypt import Bcrypt
from .database import *
from flask import redirect, url_for, flash
from flask_mail import Message
from app import app, mail
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()

# Email format
def email_format(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@newinti\.edu\.my$", email))

# Contact number format
def contact_format(contact):
    return bool(re.match(r"^01\d{8,9}$", contact))

# Password format
def password_format(password):
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,20}$", password))

# Check login validate
def check_login(loginEmail, loginPassword):
    if not loginEmail or not loginPassword:
        return False, "Both fields are required."

    user = User.query.filter_by(email=loginEmail).first()
    if not user or not bcrypt.check_password_hash(user.password, loginPassword):
        return False, "Invalid Email address or password."

    return True, user.userid

# Check register userID, userEmail, userContact can't be same as inside database
def check_register(registerID, registerEmail, registerContact):
    user_exists = User.query.filter(
        (User.userid == registerID) |
        (User.email == registerEmail) | 
        (User.contact == registerContact)
    ).first()

    if user_exists:
        if user_exists.userid == registerID:
            return False, "User ID already exists."
        elif user_exists.email == registerEmail:
            return False, "Email address already registered."
        elif user_exists.contact == registerContact:
            return False,  "Contact number already registered."

    return True, ""

# Check the Email validate or not and send reset password link based on that Email
def check_forgotPasswordEmail(forgotEmail):
    user = User.query.filter_by(email=forgotEmail).first()

    if not user:
        return False, "Invalid Email Address."

    token = serializer.dumps(forgotEmail, salt='password-reset-salt')
    reset_link = url_for('reset_password_page', token=token, _external=True)

    msg = Message('InvigilateX - Password Reset Request', recipients=[forgotEmail])
    msg.body = f'''Hi,

We received a request to reset your password for your InvigilateX account.

To reset your password, please click the link below:
{reset_link}

If you did not request this change, please ignore this email.

Thank you,
The InvigilateX Team'''
    try:
        mail.send(msg)
        flash(f"Reset email sent to {forgotEmail}!", "success")
        return True, None
    except Exception as e:
        return False, f"Failed to send email. Error: {str(e)}"



def check_resetPassword(token, resetPassword1, resetPassword2):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour
    except Exception:
        return None, "The reset link is invalid or has expired."

    if not resetPassword1 or not resetPassword2:
        return None, "All fields are required."
    elif resetPassword1 != resetPassword2:
        return None, "Passwords do not match."
    elif not password_format(resetPassword1):
        return None, "Wrong password format."
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return None, "User not found."
    
    hashed_pw = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
    user.password = hashed_pw
    db.session.commit()
    
    return user, None









# Staff Id format
# Pending


