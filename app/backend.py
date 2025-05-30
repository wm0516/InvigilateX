import re
from flask_bcrypt import Bcrypt
from .database import *
from flask import url_for, flash
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

# Staff Id format
# Pending

# Check login validate
def check_login(role, loginEmail, loginPassword):
    if not loginEmail or not loginPassword:
        return False, "Both fields are required."

    role_mapping = {
        'admin': {
            'model': Admin,
            'email_field': 'adminEmail',
            'password_field': 'adminPassword',
            'id_field': 'adminId',
        },
        'dean': {
            'model': Dean,
            'email_field': 'deanEmail',
            'password_field': 'deanPassword',
            'id_field': 'deanId',
        },
        'lecturer': {
            'model': Lecturer,
            'email_field': 'lecturerEmail',
            'password_field': 'lecturerPassword',
            'id_field': 'lecturerId',
        }
    }

    if role not in role_mapping:
        return False, "Invalid role."

    mapping = role_mapping[role]
    model = mapping['model']
    email_field = getattr(model, mapping['email_field'])

    user = model.query.filter(email_field == loginEmail).first()

    if not user or not bcrypt.check_password_hash(getattr(user, mapping['password_field']), loginPassword):
        return False, "Invalid Email address or password."

    return True, getattr(user, mapping['id_field'])

# Check registerID, registerEmail, registerContact can't be same as inside database based on role
def check_register(role, registerID, registerEmail, registerContact):
    role_mapping = {
        'admin': {
            'model': Admin,
            'id_field': 'adminId',
            'email_field': 'adminEmail',
            'contact_field': 'adminContact',
        },
        'dean': {
            'model': Dean,
            'id_field': 'deanId',
            'email_field': 'deanEmail',
            'contact_field': 'deanContact',
        },
        'lecturer': {
            'model': Lecturer,
            'id_field': 'lecturerId',
            'email_field': 'lecturerEmail',
            'contact_field': 'lecturerContact',
        }
    }

    if role not in role_mapping:
        return False, "Invalid role."

    model = role_mapping[role]['model']
    id_field = getattr(model, role_mapping[role]['id_field'])
    email_field = getattr(model, role_mapping[role]['email_field'])
    contact_field = getattr(model, role_mapping[role]['contact_field'])

    existing_user = model.query.filter(
        (id_field == registerID) |
        (email_field == registerEmail) |
        (contact_field == registerContact)
    ).first()

    if existing_user:
        if getattr(existing_user, role_mapping[role]['id_field']) == registerID:
            return False, "User ID already exists."
        elif getattr(existing_user, role_mapping[role]['email_field']) == registerEmail:
            return False, "Email address already registered."
        elif getattr(existing_user, role_mapping[role]['contact_field']) == registerContact:
            return False, "Contact number already registered."

    return True, ""


# Check the Email validate or not and send reset password link based on that Email
def check_forgotPasswordEmail(role, forgotEmail):
    role_mapping = {
        'admin': {
            'model': Admin,
            'email_field': 'adminEmail',
            'page_field': 'admin_resetPassword',
        },
        'dean': {
            'model': Dean,
            'email_field': 'deanEmail',
            'page_field': 'dean_resetPassword',
        },
        'lecturer': {
            'model': Lecturer,
            'email_field': 'lecturerEmail',
            'page_field': 'lecturer_resetPassword',
        }
    }

    if role not in role_mapping:
        return False, "Invalid role."

    mapping = role_mapping[role]
    model = mapping['model']
    email_field = getattr(model, mapping['email_field'])

    user = model.query.filter(email_field == forgotEmail).first()

    if not user:
        return False, "Invalid Email Address."

    token = serializer.dumps(forgotEmail, salt='password-reset-salt')
    reset_link = url_for(mapping['page_field'], token=token, _external=True)

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


# Check the both password and update the latest password based on the token (that user)
def check_resetPassword(role, token, resetPassword1, resetPassword2):
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

    # Role mapping
    role_mapping = {
        'admin': {
            'model': Admin,
            'email_field': 'adminEmail',
            'password_field': 'adminPassword'
        },
        'dean': {
            'model': Dean,
            'email_field': 'deanEmail',
            'password_field': 'deanPassword'
        },
        'lecturer': {
            'model': Lecturer,
            'email_field': 'lecturerEmail',
            'password_field': 'lecturerPassword'
        }
    }

    if role not in role_mapping:
        return None, "Invalid role."

    mapping = role_mapping[role]
    model = mapping['model']
    email_column = getattr(model, mapping['email_field'])
    user = model.query.filter(email_column == email).first()

    if not user:
        return None, f"{role.capitalize()} not found."

    # Update password
    hashed_pw = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
    setattr(user, mapping['password_field'], hashed_pw)

    db.session.commit()
    return user, None


# Check no duplicate exam sessions occur
def unique_examDetails(exam_CourseSectionCode, exam_Date, exam_StartTime, exam_EndTime):
    exam_exists = ExamDetails.query.filter_by(
        examDate=exam_Date,
        examStartTime=exam_StartTime,
        examEndTime=exam_EndTime,
        examCourseSectionCode=exam_CourseSectionCode
    ).first()

    if exam_exists:
        return False, "Duplicate entry exists with same course/section, date, and time."

    return True, ""

# (Need double check the purpose) Check upload lecturer
def unique_LecturerDetails(id, email, contact):
    exists = Lecturer.query.filter(
        (Lecturer.lecturerId == id) |
        (Lecturer.lecturerEmail == email) |
        (Lecturer.lecturerContact == contact)
    ).first()

    if exists:
        return False, "Duplicate entry"
    return True, ""









