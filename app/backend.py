import re
from flask_bcrypt import Bcrypt
from .database import *
from flask import redirect, url_for, flash, session
from flask_mail import Message
from app import app, mail
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()
from functools import wraps

# constants.py or at the top of your app.py
ADMIN = 4
DEAN = 3
HOP = 2
LECTURER = 1

# Email format
def email_format(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@newinti\.edu\.my$", email))



# Contact number format
def contact_format(contact):
    return bool(re.match(r"^01\d{8,9}$", contact))



# Password format
def password_format(password):
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,20}$", password))


# Check unique Contact
def check_contact(contact):
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number already registered."
    
    return True, ""


# Check unique department code and name
def check_department(code, name):
    # Check if any required field is empty
    if not code or not name:
        return False, "Please fill in all required fields."
    # Check for duplicates
    existing_departmentCode = Department.query.filter(Department.departmentCode == code).first()
    if existing_departmentCode:
        return False, "Department Code already registered."
    existing_departmentName = Department.query.filter(Department.departmentName == name).first()
    if existing_departmentName:
        return False, "Department Name already registered."
    return True, ""


def check_course(code, section, name, hour):
    if not all([code, section, name, hour]):
        return False, "Please fill in all required fields."

    courseCodeSection_text = (code + '/' + section)
    existing_courseCodeSection = Course.query.filter(Course.courseCodeSection.ilike(courseCodeSection_text)).first()
    if existing_courseCodeSection:
        return False, "Course already registered."

    return True, ""



# Check login validate
def check_login(loginEmail, loginPassword):

    user = User.query.filter_by(userEmail=loginEmail).first()
    if not user: # or not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid email or password.", None
    
    if not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid password.", None 

    if user.userLevel not in [ADMIN, DEAN, HOP, LECTURER]:
        return False, "User role is not recognized.", None

    return True, user.userId, user.userLevel


# Check registerID, registerEmail, registerContact can't be same as inside database based on role
def check_register(id, email, contact, name, password1, password2, department, role):

    role_map = {
        'LECTURER': LECTURER,
        'DEAN': DEAN,
        'HOP': HOP,
        'ADMIN': ADMIN
    }

    if not all([id, email, contact, name, password1, password2, department, role]):
        return False, "All fields are required."
    elif not email_format(email):
        return False, "Wrong Email Address format"
    elif not contact_format(contact):
        return False, "Wrong Contact Number format"
    elif password1 != password2:
        return False, "Passwords do not match."
    elif not password_format(password1):
        return False, "Wrong password format."
    elif role not in role_map:
        return False, "Invalid role selected."


    existing_id = User.query.filter(User.userId == id).first()
    if existing_id:
        return False, "Id already exists."
    
    existing_email = User.query.filter(User.userEmail == email).first()
    if existing_email:
        return False, "Email already exists."
    
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number already exists."

    return True, ""



# Check the Email validate or not and send reset password link based on that Email
def check_forgotPasswordEmail(forgotEmail):
    if not forgotEmail:
        return False, "Email address is required."

    user = User.query.filter_by(userEmail=forgotEmail).first()
    if not user:
        return False, "No account associated with this email."

    try:
        email_to_reset = user.userEmail
        token = serializer.dumps(email_to_reset, salt='password-reset-salt')
        reset_link = url_for("resetPassword", token=token, _external=True)

        msg = Message('InvigilateX - Password Reset Request', recipients=[email_to_reset])
        msg.body = f'''Hi,

We received a request to reset your password for your InvigilateX account.

To reset your password, please click the link below:
{reset_link}

If you did not request this change, please ignore this email.

Thank you,  
The InvigilateX Team'''

        mail.send(msg)
        return True, None
    except Exception as e:
        return False, f"Failed to send email. Error: {str(e)}"



# Check the both password and update the latest password based on the token (that user)
def check_resetPassword(token, resetPassword1, resetPassword2):
    try:
        # Decode token to get the email
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # Valid for 1 hour
    except Exception:
        return None, "The reset link is invalid or has expired."

    # Validation checks
    if not resetPassword1 or not resetPassword2:
        return None, "All fields are required."
    if resetPassword1 != resetPassword2:
        return None, "Passwords do not match."
    if not password_format(resetPassword1):
        return None, "Wrong password format."

    # Find the user by email
    user = User.query.filter_by(userEmail=email).first()
    if not user:
        return None, "User not found."

    # Update user password with encryption
    user.userPassword = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
    db.session.commit()
    return user, None



def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            user_role = session.get('user_role')

            if not user_id or user_role != required_role:
                flash("Unauthorized access", "error")
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator



def check_exam(courseSection, date, starttime, endtime, day, program, lecturer, student, venue):
    # Prevent querying if any required value is empty or None
    if not all([courseSection, date, starttime, endtime, day, program, lecturer, student, venue]):
        return False, "Please fill in all required fields.."

    exam_exists = Exam.query.filter_by(
        examDate=date,
        examStartTime=starttime,
        examEndTime=endtime,
        examCourseSectionCode=courseSection
    ).first()

    if exam_exists:
        return False, "Exam with same course/section, date, and time already registered."

    return True, ""



# (Need double check the purpose) Check upload lecturer
def check_lecturer(id, email, contact, name, department, role):
    if not all([id, email, contact, name, department, role]):
        return False, "Please fill in all required fields."
    
    if not email_format(email):
        return False, "Wrong Email Address format"

    if not contact_format(contact):
        return False, "Wrong Contact Number format"
    
    existing_id = User.query.filter(User.userId == id).first()
    if existing_id:
        return False, "Id already exists."
    
    existing_email = User.query.filter(User.userEmail == email).first()
    if existing_email:
        return False, "Email already exists."
    
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number already exists."
    
    return True, ""










