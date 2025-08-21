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
ADMIN = 4
HOP = 3
DEAN = 2
LECTURER = 1

# Declare the Role Map of User Level
role_map = {
    'LECTURER': LECTURER,
    'DEAN': DEAN,
    'HOP': HOP,
    'ADMIN': ADMIN
}





# Basic Validation Function 1: Email Format [End with @newinti.edu.my]
def email_format(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@newinti\.edu\.my$", email))

# Basic Validation Function 2: Contact Number Format [Start With 01 and Total Length in Between 10-11]
def contact_format(contact):
    return bool(re.match(r"^01\d{8,9}$", contact))

# Basic Validation Function 3: Password Format [With Min 8-20 Length and Include Special Character]
def password_format(password):
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,20}$", password))

# Basic Validation Function 4: Check Unique Contact [Contact Was Unique in Database]
def check_contact(contact):
    existing_contact = User.query.filter(User.userContact == contact).first()
    if existing_contact:
        return False, "Contact Number Already Registered"
    return True, ""










# FrontPart Validation Function 1: Check Login [Email and Password]
def check_login(loginEmail, loginPassword):
    user = User.query.filter_by(userEmail=loginEmail).first()
    if not user:
        return False, "Invalid Email or Password", None
    if not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid Password", None 
    if user.userLevel not in [ADMIN, DEAN, HOP, LECTURER]:
        return False, "User Role is NotRecognized", None

    return True, user.userId, user.userLevel

# FrontPart Validation Function 2: Check Access [If Not User Will Show "Unauthorized Access"]
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

# FrontPart Validation Function 3: Check Register [ID, Email, and Contact must be unique]
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

# FrontPart Validation Function 4: Check Forgot Password [Email User to Send Reset Password Link]
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

# FrontPart Validation Function 5: Check Reset Password [Must with Token(userId), and Both Password Must Be Same]
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










# Admin Validation Function 1: Check Course [Course Code/Section Must be Unique in Database, and Hour Must be Integer]
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

# Admin Validation Function 2: Check Department [Department Code and Name Must be Unique in Database]
def check_department(code, name):
    # Check for duplicates
    existing_departmentCode = Department.query.filter(Department.departmentCode == code).first()
    if existing_departmentCode:
        return False, "Department Code Already Registered"
    
    existing_departmentName = Department.query.filter(Department.departmentName == name).first()
    if existing_departmentName:
        return False, "Department Name Already Registered"
    
    return True, ""

# Admin Validation Function 3: Check Venue [Venue Room Must be Unique in Database, and Capacity Must be Integer]
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

# Admin Validation Function 4: Check Exam [Exam Date, StartTime, EndTime, and CourseSectionCode Must be Unique in Database]
def check_exam(courseSection, date, starttime, endtime):
    # 1. Convert start/end time strings into datetime
    start_dt = datetime.combine(date, datetime.strptime(starttime, "%H:%M").time())
    end_dt = datetime.combine(date, datetime.strptime(endtime, "%H:%M").time())

    # 2. Find the course
    course = Course.query.filter_by(courseCodeSection=courseSection).first()
    if not course:
        return False, f"Course {courseSection} not found"

    # 3. Check if this course already has an exam
    exam_for_course = Exam.query.filter_by(examId=course.courseExamId).first()
    if exam_for_course and exam_for_course.examDate is not None:
        return False, f"Course {courseSection} already has an exam scheduled"

    # 4. Check if another exam is already happening at the same datetime
    exam_exists = Exam.query.filter_by(
        examDate=date,
        examStartTime=start_dt,
        examEndTime=end_dt
    ).first()
    if exam_exists:
        return False, "An exam is already scheduled at the same date and time"

    return True, ""

def check_exam(courseSection, date, starttime, endtime, venue):
    # Parse date + time → datetime
    start_dt = datetime.combine(date, datetime.strptime(starttime, "%H:%M").time())
    end_dt = datetime.combine(date, datetime.strptime(endtime, "%H:%M").time())

    # Handle overnight exams (e.g. 22:00 → 02:00 next day)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    # 1. Find the course
    course = Course.query.filter_by(courseCodeSection=courseSection).first()
    if not course:
        return False, f"Course {courseSection} not found"

    # 2. Check if this course already has an exam
    exam_for_course = Exam.query.filter_by(examId=course.courseExamId).first()
    if exam_for_course and exam_for_course.examDate is not None:
        return False, f"Course {courseSection} already has an exam scheduled"

    # 3. Check if another exam overlaps (same day/time range)
    clash = Exam.query.filter(
        Exam.examDate == date,
        Exam.examStartTime < end_dt,
        Exam.examEndTime > start_dt,
        Exam.examVenue == venue
    ).first()
    if clash:
        return False, "Another exam already overlaps with this time slot"

    return True, ""



def get_available_venues(examDate, startTime, endTime):
    # Return a list of venueNumbers that are AVAILABLE during the given exam slot.
    available_venues = Venue.query.filter_by(venueStatus="AVAILABLE").all()
    usable_venues = []

    for venue in available_venues:
        conflicting = VenueAvailability.query.filter(
            VenueAvailability.venueNumber == venue.venueNumber,
            or_(
                and_(
                    VenueAvailability.startDateTime <= startTime,
                    VenueAvailability.endDateTime > startTime
                ),
                and_(
                    VenueAvailability.startDateTime < endTime,
                    VenueAvailability.endDateTime >= endTime
                ),
                and_(
                    VenueAvailability.startDateTime >= startTime,
                    VenueAvailability.endDateTime <= endTime
                )
            ),
            VenueAvailability.status.in_(["UNAVAILABLE", "IN SERVICE"])
        ).first()

        if not conflicting:
            usable_venues.append(venue.venueNumber)

    return usable_venues


def create_exam_and_related(examDate, examDay, startTime, endTime, courseSection, venue_text, practicalLecturer, tutorialLecturer, invigilatorNo):
    # 1. Find the course
    course = Course.query.filter_by(courseCodeSection=courseSection).first()
    if not course:
        raise ValueError(f"Course with section {courseSection} not found")

    # 2. Find the related exam
    exam = Exam.query.filter_by(examId=course.courseExamId).first()
    if not exam:
        raise ValueError(f"Exam for course {courseSection} not found")

    # 3. Update the exam details
    exam.examDate = examDate
    exam.examDay = examDay
    exam.examStartTime = startTime
    exam.examEndTime = endTime
    exam.examVenue = venue_text
    exam.examNoInvigilator = invigilatorNo

    # 4. Update lecturer assignments if needed
    course.coursePractical = practicalLecturer
    course.courseTutorial = tutorialLecturer

    # 5. Save Venue Availability (convert date + time into datetime)
    start_dt = datetime.combine(examDate, datetime.strptime(startTime, "%H:%M:%S").time())
    end_dt = datetime.combine(examDate, datetime.strptime(endTime, "%H:%M:%S").time())

    if end_dt <= start_dt:  # overnight case
        end_dt += timedelta(days=1)

    new_availability = VenueAvailability(
        venueNumber=venue_text,
        startDateTime=start_dt,
        endDateTime=end_dt,
        status="UNAVAILABLE"
    )
    db.session.add(new_availability)

    # 6. Create Invigilation Report
    new_report = InvigilationReport(examId=exam.examId)
    db.session.add(new_report)
    db.session.flush()  # ensures invigilationReportId is available

    # 7. Calculate Exam Duration
    pending_hours = (end_dt - start_dt).total_seconds() / 3600.0

    # 8. Get Eligible Invigilators (exclude lecturers)
    exclude_ids = [uid for uid in [practicalLecturer, tutorialLecturer] if uid]
    eligible_invigilators = User.query.filter(
        ~User.userId.in_(exclude_ids),
        User.userLevel == 1
    ).all()

    if not eligible_invigilators:
        raise ValueError("No eligible invigilators available for assignment.")

    # 9. Sort Eligible Invigilators by workload
    eligible_invigilators.sort(
        key=lambda inv: (inv.userCumulativeHours or 0) + (inv.userPendingCumulativeHours or 0)
    )

    # 10. Assign Invigilators
    for _ in range(invigilatorNo):
        if not eligible_invigilators:
            break

        lowest_hours = (eligible_invigilators[0].userCumulativeHours or 0) + \
                       (eligible_invigilators[0].userPendingCumulativeHours or 0)

        lowest_candidates = [
            inv for inv in eligible_invigilators
            if ((inv.userCumulativeHours or 0) + (inv.userPendingCumulativeHours or 0)) == lowest_hours
        ]

        chosen = random.choice(lowest_candidates)
        chosen.userPendingCumulativeHours = (chosen.userPendingCumulativeHours or 0) + pending_hours

        attendance = InvigilatorAttendance(
            reportId=new_report.invigilationReportId,
            invigilatorId=chosen.userId,
            checkIn=None,
            checkOut=None,
            remark=None
        )
        db.session.add(attendance)

        eligible_invigilators.remove(chosen)

    # 11. Final Commit
    db.session.commit()

    return exam



# Admin Validation Function 5: Check Lecturer [Id, Email, Contact Must be Unique in Database]
def check_staff(id, email, contact):
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

# Admin Validation Function 6: Check Profile [Contact Must be Unique in Database, and Both Password Must be Same]
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
























