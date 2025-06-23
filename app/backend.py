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

# Check unique contact 
def check_contact(contact):
    existing_user = User.query.filter(User.userContact == contact).first()
    existing_admin = Admin.query.filter(Admin.adminContact == contact).first()

    if existing_user or existing_admin:
        return False, "Contact number already registered."
    return True, ""



# Staff Id format
# Pending

# Check login validate
'''def check_login(role, loginEmail, loginPassword):
    if not loginEmail or not loginPassword:
        return False, "Both fields are required."
    
    if role == 'admin':
        admin = Admin.query.filter_by(adminEmail=loginEmail).first()
        if admin and bcrypt.check_password_hash(admin.adminPassword, loginPassword):
            return True, admin.adminId
        else:
            return False, "Invalid email or password."

    user = User.query.filter_by(userEmail=loginEmail).first()
    if not user or not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid email or password."

    level_to_role = {
        3: 'admin',
        2: 'dean',
        1: 'lecturer'
    }

    user_role = level_to_role.get(user.userLevel)
    if not user_role:
        return False, "User role is not recognized."

    # Enforce access control if role is required
    if role and user_role != role:
        return False, f"No access to the {role} page."

    return True, user.userId
'''

# Check registerID, registerEmail, registerContact can't be same as inside database based on role
def check_register(registerID, registerEmail, registerContact):
    # Check in User table
    existing_user = User.query.filter(
        (User.userId == registerID) |
        (User.userEmail == registerEmail) |
        (User.userContact == registerContact)
    ).first()
    
    # Check in Admin table
    existing_admin = Admin.query.filter(
        (Admin.adminId == registerID) |
        (Admin.adminEmail == registerEmail) |
        (Admin.adminContact == registerContact)
    ).first()

    if existing_user or existing_admin:
        if (existing_user and existing_user.userId == registerID) or \
           (existing_admin and existing_admin.adminId == registerID):
            return False, "ID already exists."
        
        if (existing_user and existing_user.userEmail == registerEmail) or \
           (existing_admin and existing_admin.adminEmail == registerEmail):
            return False, "Email address already registered."
        
        if (existing_user and existing_user.userContact == registerContact) or \
           (existing_admin and existing_admin.adminContact == registerContact):
            return False, "Contact number already registered."

    return True, ""



# Check the Email validate or not and send reset password link based on that Email
def check_forgotPasswordEmail(role, forgotEmail):
    role_levels = {
        'admin': 3, 
        'dean': 2, 
        'lecturer': 1
    }

    if role not in role_levels:
        return False, "Invalid role."

    if role == 'admin':
        admin = Admin.query.filter_by(adminEmail=forgotEmail).first()
        if not admin:
            return False, "Invalid Email Address."
        if admin.adminLevel != role_levels[role]:
            return False, f"No access to the {role} reset page."
    else:
        user = User.query.filter_by(userEmail=forgotEmail).first()
        if not user:
            return False, "Invalid Email Address."
        if user.userLevel != role_levels[role]:
            return False, f"No access to the {role} reset page."

    try:
        email_to_reset = admin.adminEmail if role == 'admin' else user.userEmail
        token = serializer.dumps(email_to_reset, salt='password-reset-salt')
        reset_link = url_for(f"{role}_resetPassword", token=token, _external=True)

        msg = Message('InvigilateX - Password Reset Request', recipients=[email_to_reset])
        msg.body = f'''Hi,

We received a request to reset your password for your InvigilateX account.

To reset your password, please click the link below:
{reset_link}

If you did not request this change, please ignore this email.

Thank you,  
The InvigilateX Team'''

        mail.send(msg)
        flash(f"Reset email sent to {email_to_reset}!", "success")
        return True, None
    except Exception as e:
        return False, f"Failed to send email. Error: {str(e)}"







# Check the both password and update the latest password based on the token (that user)
def check_resetPassword(role, token, resetPassword1, resetPassword2):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiry
    except Exception:
        return None, "The reset link is invalid or has expired."

    if not resetPassword1 or not resetPassword2:
        return None, "All fields are required."
    if resetPassword1 != resetPassword2:
        return None, "Passwords do not match."
    if not password_format(resetPassword1):
        return None, "Wrong password format."

    role_levels = {'admin': 3, 'dean': 2, 'lecturer': 1}
    if role not in role_levels:
        return None, "Invalid role."

    if role == 'admin':
        admin = Admin.query.filter_by(adminEmail=email).first()
        if not admin:
            return None, "Admin not found."
        if admin.adminLevel != role_levels[role]:
            return None, f"No access to reset password as {role}."

        # Update admin password
        admin.adminPassword = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
        db.session.commit()
        return admin, None

    else:
        user = User.query.filter_by(userEmail=email).first()
        if not user:
            return None, "User not found."
        if user.userLevel != role_levels[role]:
            return None, f"No access to reset password as {role}."

        # Update user password
        user.userPassword = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
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









