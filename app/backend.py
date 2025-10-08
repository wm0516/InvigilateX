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
import random
from datetime import datetime, timedelta
from sqlalchemy import and_, or_


# constants.py or at the top of your app.py
ADMIN = 5
HOP = 4
HOS = 3
DEAN = 2
LECTURER = 1

# Declare the Role Map of User Level
role_map = {
    'LECTURER': LECTURER,
    'DEAN': DEAN,
    'HOS': HOS,
    'HOP': HOP,
    'ADMIN': ADMIN
}



# Basic User Details Function
# -------------------------------
# Basic User Details Function 1: Email Format [End with @newinti.edu.my]
# -------------------------------
def email_format(email):
    return email
    # return bool(re.match(r"^[a-zA-Z0-9._%+-]+@newinti\.edu\.my$", email))

# -------------------------------
# Basic User Details Function 2: Contact Number Format [Start With 01 and Total Length in Between 10-11]
# -------------------------------
def contact_format(contact):
    return bool(re.match(r"^01\d{8,9}$", contact))

# -------------------------------
# Basic User Details Function 3: Password Format [With Min 8-20 Length and Include Special Character]
# -------------------------------
def password_format(password):
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,20}$", password))

# -------------------------------
# Basic User Details Function 4: Check Unique Contact [Contact Was Unique in Database]
# -------------------------------
def check_contact(contact):
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number Already Registered"
    return True, ""





# Auth Function
# -------------------------------
# Auth Function 1: Check Login [Email and Password]
# -------------------------------
def check_login(loginEmail, loginPassword):
    user = User.query.filter_by(userEmail=loginEmail).first()
    if not user:
        return False, "Invalid Email or Password", None
    if not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid Password", None 
    if user.userLevel not in [ADMIN, DEAN, HOS, HOP, LECTURER]:
        return False, "User Role is NotRecognized", None

    return True, user.userId, user.userLevel

# -------------------------------
# Auth Function 2: Check Access [If Not User Will Show "Unauthorized Access"]
# -------------------------------
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

# -------------------------------
# Auth Function 3: Check Register [ID, Email, and Contact must be unique]
# -------------------------------
def check_register(id, email, contact, password1, password2):
    if not email_format(email):
        return False, "Wrong Email Address Format"
    elif not contact_format(contact):
        return False, "Wrong Contact Number Format"
    elif password1 != password2:
        return False, "Passwords Do Not Match"
    elif not password_format(password1):
        return False, "Wrong Password Format"

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

# -------------------------------
# Auth Function 4: Check Forgot Password [Email User to Send Reset Password Link]
# -------------------------------
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
    

def send_verifyActivateLink(email):
    user = User.query.filter_by(userEmail=email).first()
    if not user:
        return False, "No Account Associated With This Email."

    try:
        email_to_verify = user.userEmail
        # Generate token for verification
        token = serializer.dumps(email_to_verify, salt='account-verify-salt')
        verify_link = url_for("verifyAccount", token=token, _external=True)

        msg = Message('InvigilateX - Verify Your Account', recipients=[email_to_verify])
        msg.body = f'''Hi,

Thank you for registering for InvigilateX!

Please verify your account by clicking the link below:
{verify_link}

If you did not register for an account, please ignore this email.

Thank you,  
The InvigilateX Team'''
        
        mail.send(msg)
        return True, None
    except Exception as e:
        return False, f"Failed to Send Email. Error: {str(e)}"


# -------------------------------
# Auth Function 5: Check Reset Password [Must with Token(userId), and Both Password Must Be Same]
# -------------------------------
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








# Admin Function
# -------------------------------
# Admin Function 1: Create Course with Automatically Exam when with all correct data
# -------------------------------
def create_course_and_exam(department, code, section, name, hour, practical, tutorial, students, status):
    # Validate department code
    department_name = Department.query.filter_by(departmentCode=department.upper() if department else None).first()
    if not department_name:
        department = None
    else:
        department = department.upper()

    # Validate practical lecturer
    practical_user = User.query.filter_by(userId=practical if practical else None).first()
    if practical_user:
        practical_id = practical_user.userId
    else:
        practical_id = None

    # Validate tutorial lecturer
    tutorial_user = User.query.filter_by(userId=tutorial if tutorial else None).first()
    if tutorial_user:
        tutorial_id = tutorial_user.userId
    else:
        tutorial_id = None

    courseCodeSection_text = (code + '/' + section)
    existing_courseCodeSection = Course.query.filter(Course.courseCodeSectionIntake.ilike(courseCodeSection_text)).first()
    if existing_courseCodeSection:
        return False, "Course Already Registered"
    
    # Validate 'hour'
    try:
        hour = int(hour)
    except ValueError:
        return False, "Hour must be an integer"
    if hour < 0:
        return False, "Hour cannot be negative"
    
    # Validate 'students'
    try:
        students = int(students)
    except ValueError:
        return False, "Students must be an integer"
    if students < 0:
        return False, "Students cannot be negative"
        
    if students > 32:
        invigilatorNo = 3
    else: 
        invigilatorNo = 2

    # Only create an Exam if both lecturers are valid
    exam_id = None
    if practical_user and tutorial_user:
        new_exam = Exam(
            examVenue=None,
            examStartTime=None,
            examEndTime=None,
            examNoInvigilator=invigilatorNo
        )
        db.session.add(new_exam)
        db.session.flush()  # Get the examId before commit
        exam_id = new_exam.examId

    # Create the Course
    new_course = Course(
        courseCodeSectionIntake=f"{code}/{section}".upper() if code and section else None,
        courseDepartment=department,
        courseName=name.upper() if name else None,
        courseHour=hour,
        courseStudent=students,
        coursePractical=practical_id,
        courseTutorial=tutorial_id,
        courseExamId=exam_id,  # Assign examId if exists, else None
        courseStatus=status
    )
    db.session.add(new_course)
    db.session.commit()
    return True, "Course created successfully"



# -------------------------------
# Admin Function 2: Fill in Exam details and Automatically VenueAvailability, InvigilationReport, InvigilatorAttendance
# -------------------------------
def create_exam_and_related(start_dt, end_dt, courseSection, venue_text, practicalLecturer, tutorialLecturer, invigilatorNo):
    venue_place = Venue.query.filter_by(venueNumber=venue_text.upper() if venue_text else None).first()
    if not venue_place:
        venue_text = None
    else:
        venue_text = venue_text.upper()

    course = Course.query.filter_by(courseCodeSectionIntake=courseSection).first()
    if not course:
        return False, f"Course with section {courseSection} not found"

    exam = Exam.query.filter_by(examId=course.courseExamId).first()
    if not exam:
        return False, f"Exam for course {courseSection} not found"

    # Auto-set invigilator count
    invigilatorNo = invigilatorNo or (3 if (course.courseStudent or 0) > 32 else 2)

    # Validate the value
    try:
        invigilatorNo = int(invigilatorNo)
    except ValueError:
        return False, "Number of Invigilators must be an integer"

    if invigilatorNo < 1:
        return False, "Number of Invigilators must be at least 1"

    # Update exam details
    exam.examStartTime = start_dt
    exam.examEndTime = end_dt
    exam.examVenue = venue_text
    exam.examNoInvigilator = invigilatorNo

    # Assign lecturers
    if practicalLecturer:
        lecturer_user = User.query.filter(
            or_(
                User.userId == practicalLecturer,
                User.userName.ilike(practicalLecturer)
            )
        ).first()
        if not lecturer_user:
            return False, f"Lecturer '{practicalLecturer}' not found in User table"

        course.coursePractical = lecturer_user.userId
        course.courseTutorial = lecturer_user.userId
    else:
        course.coursePractical = None
        course.courseTutorial = None  

    # Adjust end time if necessary
    adj_end_dt = end_dt
    if end_dt <= start_dt:
        adj_end_dt = end_dt + timedelta(days=1)

    # Clean old records first
    delete_exam_related(exam.examId, commit=False)

    # create new availability
    if venue_text:
        new_availability = VenueAvailability(
            venueNumber=venue_text,
            startDateTime=start_dt,
            endDateTime=adj_end_dt,
            examId=exam.examId
        )
        db.session.add(new_availability)

    # Create new report
    new_report = InvigilationReport(examId=exam.examId)
    db.session.add(new_report)
    db.session.flush()

    pending_hours = (adj_end_dt - start_dt).total_seconds() / 3600.0

    # Exclude lecturers
    exclude_ids = [uid for uid in [practicalLecturer, tutorialLecturer] if uid]
    eligible_invigilators = User.query.filter(
        ~User.userId.in_(exclude_ids),
        User.userLevel == 1,
        User.userStatus == True
    ).all()

    if not eligible_invigilators:
        return False, "No eligible invigilators available for assignment"

    # Split by gender
    male_invigilators = [inv for inv in eligible_invigilators if inv.userGender == "MALE"]
    female_invigilators = [inv for inv in eligible_invigilators if inv.userGender == "FEMALE"]

    # Sort by workload
    def workload(inv):
        return (inv.userCumulativeHours or 0) + (inv.userPendingCumulativeHours or 0)

    male_invigilators.sort(key=workload)
    female_invigilators.sort(key=workload)

    chosen_invigilators = []

    if invigilatorNo == 1:
        pool = sorted(male_invigilators + female_invigilators, key=workload)
        if not pool:
            return False, "No available invigilators"
        chosen_invigilators = [pool[0]]
    else:
        if not male_invigilators or not female_invigilators:
            return False, "Need both male and female invigilators when assigning 2 or more"

        chosen_invigilators = [male_invigilators.pop(0), female_invigilators.pop(0)]
        pool = sorted(male_invigilators + female_invigilators, key=workload)
        chosen_invigilators += pool[:invigilatorNo - 2]

    if len(chosen_invigilators) < invigilatorNo:
        return False, f"Not enough invigilators available. Required: {invigilatorNo}, Available: {len(chosen_invigilators)}"

    for chosen in chosen_invigilators:
        chosen.userPendingCumulativeHours = (chosen.userPendingCumulativeHours or 0) + pending_hours
        attendance = InvigilatorAttendance(
            reportId=new_report.invigilationReportId,
            invigilatorId=chosen.userId,
            timeCreate=datetime.now(timezone.utc)
        )
        db.session.add(attendance)

    db.session.commit()
    return True, "Exam created/updated successfully"



# -------------------------------
# Delete All Related Exam after get modify
# -------------------------------
def delete_exam_related(exam_id, commit=True):
    exam = Exam.query.get(exam_id)
    if not exam:
        return False, f"Exam {exam_id} not found"   

    if exam.examStartTime and exam.examEndTime:
        pending_hours = (exam.examEndTime - exam.examStartTime).total_seconds() / 3600.0
    else:
        pending_hours = 0

    # Roll back pending hours from invigilators
    reports = InvigilationReport.query.filter_by(examId=exam.examId).all()
    for report in reports:
        for att in report.attendances:
            invigilator = att.invigilator
            if invigilator:
                invigilator.userPendingCumulativeHours = max(
                    0.0,
                    (invigilator.userPendingCumulativeHours or 0.0) - pending_hours
                )

    # Delete reports and venue availability
    InvigilationReport.query.filter_by(examId=exam.examId).delete()
    VenueAvailability.query.filter_by(examId=exam.examId).delete()

    if commit:
        db.session.commit()

    return True, f"Related data for exam {exam_id} deleted successfully"







# -------------------------------
# Admin Function 3: Create Staff when with all correct data
# -------------------------------
def create_staff(id, department, name, role, email, contact, gender, hashed_pw):
    # Normalize department code
    department_code = department.upper() if department else None
    dept = Department.query.filter_by(departmentCode=department_code).first()
    if not dept:
        department_code = None  # If department doesn't exist, set to None

    # Validate email and contact
    if not email_format(email):
        return False, "Wrong Email Address Format"
    if not contact_format(contact):
        return False, "Wrong Contact Number Format"

    # Check uniqueness
    if User.query.filter_by(userId=id.upper()).first():
        return False, "Id Already exists"
    if User.query.filter_by(userEmail=email).first():
        return False, "Email Already exists"
    if User.query.filter_by(userContact=contact).first():
        return False, "Contact Number Already exists"

    # Create staff object
    new_staff = User(
        userId=id.upper(),
        userDepartment=department_code,
        userName=name.upper(),
        userLevel=role,
        userEmail=email,
        userContact=contact,
        userGender=gender,
        userPassword=hashed_pw
    )
    db.session.add(new_staff)
    db.session.flush()  # Push to DB so userId is available for FK relations

    # Assign Dean or HOP if applicable
    if dept:
        if role == 2:  # Dean
            dept.deanId = new_staff.userId
        elif role == 3: # HOS
            dept.hosId = new_staff.userId
        elif role == 4:  # HOP
            dept.hopId = new_staff.userId
        db.session.add(dept)

    db.session.commit()

    return True, "Staff created successfully"




# -------------------------------
# Admin Function 5: View and Edit Admin Profile
# -------------------------------
def check_profile(id, contact, password1, password2):
    # If contact is entered, validate format
    if contact:
        user_record = User.query.filter(User.userId == id).first()
        if not user_record:
            return False, "User not found"
        
        if not contact_format(contact):
            return False, "Wrong Contact Number Format"
        
        if contact != user_record.userContact:
            is_unique, msg = check_contact(contact)
            if not is_unique:
                return False, msg

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








