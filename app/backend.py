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

role_map = {
    'LECTURER': LECTURER,
    'DEAN': DEAN,
    'HOP': HOP,
    'ADMIN': ADMIN
}

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
        return False, "Contact Number Already Registered"
    
    return True, ""



# Check login validate
def check_login(loginEmail, loginPassword):
    user = User.query.filter_by(userEmail=loginEmail).first()
    if not user: # or not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid Email or Password", None
    if not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid Password", None 
    if user.userLevel not in [ADMIN, DEAN, HOP, LECTURER]:
        return False, "User Role is NotRecognized", None

    return True, user.userId, user.userLevel


# Check registerID, registerEmail, registerContact can't be same as inside database based on role
def check_register(id, email, contact, password1, password2, role):
    if not email_format(email):
        return False, "Wrong Email Address Format"
    elif not contact_format(contact):
        return False, "Wrong Contact Number Format"
    elif password1 != password2:
        return False, "Passwords Do Not Match"
    elif not password_format(password1):
        return False, "Wrong Password Format"
    elif role not in role_map:
        return False, "Invalid Role Selected"

    existing_id = User.query.filter(User.userId == id).first()
    if existing_id:
        return False, "Id Already Exists"
    
    existing_email = User.query.filter(User.userEmail == email).first()
    if existing_email:
        return False, "Email Already Exists"
    
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number Already Exists"

    return True, ""


# Check the Email validate or not and send reset password link based on that Email
def check_forgotPasswordEmail(forgotEmail):
    user = User.query.filter_by(userEmail=forgotEmail).first()
    if not user:
        return False, "No Account Associated With This Email."

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
        return False, f"Failed to Send Email. Error: {str(e)}"


# Check the both password and update the latest password based on the token (that user)
def check_resetPassword(token, resetPassword1, resetPassword2):
    try:
        # Decode token to get the email
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # Valid for 1 hour
    except Exception:
        return None, "The Reset Link is Invalid or Has Expired"

    # Validation checks
    if resetPassword1 != resetPassword2:
        return None, "Passwords Do Not Match"
    if not password_format(resetPassword1):
        return None, "Wrong Password Format"

    # Find the user by email
    user = User.query.filter_by(userEmail=email).first()
    if not user:
        return None, "User Not Found."

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
                flash("Unauthorized Access", "error")
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator



def check_exam(courseSection, date, starttime, endtime):
    exam_exists = Exam.query.filter_by(
        examDate=date,
        examStartTime=starttime,
        examEndTime=endtime,
        examCourseSectionCode=courseSection
    ).first()

    if exam_exists:
        return False, "Exam With Same Course/Section, Date, And Time Already Registered"

    return True, ""



# (Need double check the purpose) Check upload lecturer
def check_lecturer(id, email, contact):
    if not email_format(email):
        return False, "Wrong Email Address Format"
    if not contact_format(contact):
        return False, "Wrong Contact Number Format"
    
    existing_id = User.query.filter(User.userId == id).first()
    if existing_id:
        return False, "Id Already exists"
    existing_email = User.query.filter(User.userEmail == email).first()
    if existing_email:
        return False, "Email Already exists"
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number Already exists"
    
    return True, ""


# continue on this function
def check_profile(id, contact, password1, password2):
    # If contact is entered, validate format
    if contact:
        user_record = User.query.filter(User.userId == id).first()
        if not user_record:
            return False, "User not found"  # avoid None access
        
        if not contact_format(contact):
            return False, "Wrong Contact Number Format"
        
        if contact != user_record.userContact and check_contact(contact):
            return False, "Contact Number Already exists"

    # If any password is entered, both must be present and match
    if password1 or password2:
        if not password1 or not password2:
            return False, "Both Password Fields Are Rquired"
        if not password_format(password1) or not password_format(password2):
            return False, "Wrong Password Format"
        if password1 != password2:
            return False, "Passwords Do Not Match"
        
    if contact and not password1 and not password2:
        return True, "No Update"
    
    return True, ""



# Check unique department code and name
def check_department(code, name):
    # Check for duplicates
    existing_departmentCode = Department.query.filter(Department.departmentCode == code).first()
    if existing_departmentCode:
        return False, "Department Code Already Registered"
    
    existing_departmentName = Department.query.filter(Department.departmentName == name).first()
    if existing_departmentName:
        return False, "Department Name Already Registered"
    
    return True, ""


# Check unique venue roomNumber and floor
def check_venue(roomNumber, capacity):
    # Check for duplicates
    existing_roomNumber = Venue.query.filter(Venue.venueNumber == roomNumber).first()
    if existing_roomNumber:
        return False, "Venue Room Number Already Registered"
    
    try:
        int(capacity)
    except ValueError:
        return False, "Capacity must be in Integer"
    
    return True, ""


def check_course(code, section, hour):
    courseCodeSection_text = (code + '/' + section)
    existing_courseCodeSection = Course.query.filter(Course.courseCodeSection.ilike(courseCodeSection_text)).first()
    if existing_courseCodeSection:
        return False, "Course Already Registered"
    
    try:
        int(hour)
    except ValueError:
        return False, "Hour(s) must be in Integer"

    return True, ""




