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



# -------------------------------
# Basic User Details Function 1: Email Format [End with @newinti.edu.my]
# -------------------------------
def email_format(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@newinti\.edu\.my$", email))

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
        token = serializer.dumps(email, salt='account-verify-salt')
        verify_link = url_for("verifyAccount", token=token, _external=True)

        msg = Message('InvigilateX - Verify Your Account', recipients=[email])
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
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        return None, "The Reset Link is Invalid or Has Expired"

    if resetPassword1 != resetPassword2:
        return None, "Passwords Do Not Match"
    if not password_format(resetPassword1):
        return None, "Wrong Password Format"

    user = User.query.filter_by(userEmail=email).first()
    if not user:
        return None, "User Not Found."

    user.userPassword = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
    user.isLocked = False             # ✅ unlock the account
    user.failedAttempts = 0           # ✅ reset counter
    db.session.commit()
    return user, None


# Admin Function
# -------------------------------
# Admin Function 1: Create Course with Automatically Exam when with all correct data
# -------------------------------
def create_course_and_exam(department, code, section, name, hour, students):
    # Validate department code
    department_name = Department.query.filter_by(departmentCode=department.upper() if department else None).first()
    if not department_name:
        department = None
    else:
        department = department.upper()

    # Validate courseCodeSection
    courseCodeSection_text = f"{code}/{section}".upper() if code and section else None
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

    # Check if an Exam already exists for this course code (all sections share one exam)
    existing_exam_course = Course.query.filter(Course.courseCodeSectionIntake.ilike(f"{code}/%")).first()
    if existing_exam_course and existing_exam_course.courseExamId:
        exam_id = existing_exam_course.courseExamId
        exam = Exam.query.get(exam_id)

        # 🧮 Update total students for that exam
        total_students = db.session.query(db.func.sum(Course.courseStudent)).filter(
            Course.courseCodeSectionIntake.ilike(f"{code}/%")
        ).scalar() or 0
        exam.examTotalStudents = total_students + students  # add new section’s students
    else:
        # 🆕 Create new Exam
        new_exam = Exam(
            examStartTime=None,
            examEndTime=None,
            examNoInvigilator=None,
            examTotalStudents=students  # only this section initially
        )
        db.session.add(new_exam)
        db.session.flush()  # Get examId
        exam_id = new_exam.examId

    # ➕ Create the new Course
    new_course = Course(
        courseCodeSectionIntake=courseCodeSection_text,
        courseDepartment=department,
        courseName=name.upper() if name else None,
        courseHour=hour,
        courseStudent=students,
        courseExamId=exam_id,
        courseStatus=True
    )
    db.session.add(new_course)
    db.session.commit()
    
    return True, "Course created successfully"



# -------------------------------
# Helper: Check lecturer availability based on their timetable
# -------------------------------
def is_lecturer_available(lecturer_id, exam_start, exam_end, buffer_minutes=60):
    buffer_delta = timedelta(minutes=buffer_minutes)
    start_check = exam_start - buffer_delta
    end_check = exam_end + buffer_delta

    timetable = Timetable.query.filter_by(user_id=lecturer_id).first()
    if not timetable:
        return True  # No timetable, assume available

    for row in timetable.rows:
        try:
            # Example: row.classWeekDate = "04/07/2025-07/20/2025"
            if '-' in row.classWeekDate:
                start_str, end_str = row.classWeekDate.split('-')
                class_start_date = datetime.strptime(start_str.strip(), "%m/%d/%Y").date()
                class_end_date = datetime.strptime(end_str.strip(), "%m/%d/%Y").date()
            else:
                class_start_date = class_end_date = datetime.strptime(row.classWeekDate.strip(), "%m/%d/%Y").date()

            # If exam is after the end date, ignore this class row
            if exam_start.date() > class_end_date:
                continue

            # Parse class time
            class_start_time_str, class_end_time_str = row.classTime.split('-')
            # Combine with exam date (or actual class date if needed)
            class_start_dt = datetime.combine(class_start_date, datetime.strptime(class_start_time_str.strip(), "%H:%M").time())
            class_end_dt = datetime.combine(class_end_date, datetime.strptime(class_end_time_str.strip(), "%H:%M").time())

            # Check overlap with exam period + buffer
            if class_start_dt < end_check and class_end_dt > start_check:
                return False
        except Exception as e:
            flash(f"Error parsing timetable row {row.rowId}: {e}", "success")
            continue

    return True



# -------------------------------
# Admin Function 2: Fill in Exam details and Automatically VenueExam, InvigilationReport, InvigilatorAttendance
# -------------------------------
def create_exam_and_related(start_dt, end_dt, courseSection, venue_list, studentPerVenue_list):
    # --- Fetch course sections ---
    course_sections = Course.query.filter(Course.courseCodeSectionIntake.like(f"{courseSection}/%")).all()
    if not course_sections:
        return False, f"No course sections found for {courseSection}"

    # Shared exam ID
    exam = Exam.query.filter_by(examId=course_sections[0].courseExamId).first()
    if not exam:
        return False, f"Exam for course {courseSection} not found"

    # --- Invigilator count for this row ---
    if studentPerVenue_list:
        invigilatorNo_for_row = 3 if sum(studentPerVenue_list) > 32 else 2
        exam.examNoInvigilator = (exam.examNoInvigilator or 0) + invigilatorNo_for_row

    # --- Times ---
    exam.examStartTime = min(exam.examStartTime or start_dt, start_dt)
    exam.examEndTime = max(exam.examEndTime or end_dt, end_dt)
    adj_end_dt = end_dt if end_dt > start_dt else end_dt + timedelta(days=1)
    pending_hours = (adj_end_dt - start_dt).total_seconds() / 3600.0

    # --- Report ---
    report = InvigilationReport.query.filter_by(examId=exam.examId).first()
    if not report:
        report = InvigilationReport(examId=exam.examId)
        db.session.add(report)
        db.session.flush()

    # --- Excluded lecturers (teaching the course) ---
    exclude_ids = []
    for c in course_sections:
        flash(f"ExamId: {c.courseExamId}, Practical: {c.coursePractical}, Tutorial: {c.courseTutorial}, Lecturer: {c.courseLecturer}", "success")
        exclude_ids += [uid for uid in [c.coursePractical, c.courseTutorial, c.courseLecturer] if uid is not None]

    # --- Filter potential invigilators ---
    query = User.query.filter(User.userLevel == 1,User.userStatus == True)
    if exclude_ids:
        query = query.filter(~User.userId.in_(exclude_ids))

    # --- Flexibility checks ---
    flexible = []
    not_flexible = []

    for inv in query.all():
        total_hours = (inv.userCumulativeHours or 0) + (inv.userPendingCumulativeHours or 0)
        available = is_lecturer_available(inv.userId, start_dt, adj_end_dt)

        if total_hours < 36 and available:
            flexible.append(inv)
        else:
            not_flexible.append((inv, total_hours, available))

    eligible_invigilators = flexible
    if not eligible_invigilators:
        return False, "No eligible invigilators available due to timetable conflicts or workload limits"

    # --- Male / Female pools ---
    male = sorted(
        [i for i in eligible_invigilators if i.userGender == "MALE"],
        key=lambda x: (x.userCumulativeHours or 0) + (x.userPendingCumulativeHours or 0)
    )
    female = sorted(
        [i for i in eligible_invigilators if i.userGender == "FEMALE"],
        key=lambda x: (x.userCumulativeHours or 0) + (x.userPendingCumulativeHours or 0)
    )

    # --- Summary Flash Message (One Line) ---
    not_flex_ids = [str(i.userId) for i, t, a in not_flexible]
    not_flex_text = ", ".join(not_flex_ids) if not_flex_ids else "None"

    flash(
        f"✅ Eligible: {len(eligible_invigilators)} | "
        f"Flexible: {len(flexible)} | "
        f"Not Flexible: {len(not_flexible)}: [{not_flex_text}] | "
        f"Male: {len(male)} | Female: {len(female)}",
        "success"
    )

    # ---------------------------------------
    # Handle each venue independently
    # ---------------------------------------
    for venue_text, spv in zip(venue_list, studentPerVenue_list):
        spv = int(spv)
        venue_text = venue_text.upper()

        venue_obj = Venue.query.filter_by(venueNumber=venue_text).first()
        if not venue_obj:
            flash(f"Venue {venue_text} not found, skipping", "error")
            continue

        assigned_students = min(spv, venue_obj.venueCapacity)
        # Create venue exam
        new_venue_exam = VenueExam(
            venueNumber=venue_text,
            startDateTime=start_dt,
            endDateTime=adj_end_dt,
            examId=exam.examId,
            capacity=assigned_students
        )
        db.session.add(new_venue_exam)
        db.session.flush()

        # --- Select invigilators ---
        if invigilatorNo_for_row == 1:
            pool = sorted(
                male + female,
                key=lambda x: (x.userCumulativeHours or 0) + (x.userPendingCumulativeHours or 0)
            )
            chosen_invigilators = [pool[0]]

        else:
            if not male or not female:
                return False, "Need both male and female invigilators for 2+ invigilators"

            chosen_invigilators = [male.pop(0), female.pop(0)]

            pool = sorted(
                male + female,
                key=lambda x: (x.userCumulativeHours or 0) + (x.userPendingCumulativeHours or 0)
            )
            chosen_invigilators += pool[:invigilatorNo_for_row - 2]

        # --- Store attendance & pending hours ---
        for chosen in chosen_invigilators:
            chosen.userPendingCumulativeHours = (chosen.userPendingCumulativeHours or 0) + pending_hours

            db.session.add(
                InvigilatorAttendance(
                    reportId=report.invigilationReportId,
                    invigilatorId=chosen.userId,
                    venueNumber=venue_text,
                    timeCreate=datetime.now(timezone.utc)
                )
            )
            send_invigilator_slot_notification(chosen.userId)
    db.session.commit()
    return True, f"Exam updated for course {courseSection} with total {exam.examTotalStudents} students"


# -------------------------------
# Delete All Related Exam after get modify
# -------------------------------
def delete_exam_related(exam_id, commit=True):
    exam = Exam.query.get(exam_id)
    if not exam:
        return False, f"Exam {exam_id} not found"   

    pending_hours = 0
    if exam.examStartTime and exam.examEndTime:
        pending_hours = (exam.examEndTime - exam.examStartTime).total_seconds() / 3600.0

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
        db.session.delete(report)  # Use ORM delete to trigger cascade

    VenueExam.query.filter_by(examId=exam.examId).delete()

    if commit:
        db.session.commit()

    return True, f"Related data for exam {exam_id} deleted successfully"

# -------------------------------
# Admin Function 3: Create Staff when with all correct data
# -------------------------------
def create_staff(id, department, name, role, email, contact, gender, hashed_pw, cardId):
    # Normalize department code
    department_code = department.upper() if department else None
    dept = Department.query.filter_by(departmentCode=department_code).first()
    if not dept:
        department_code = None  # If department doesn't exist, set to None

    # Validate email and contact
    if not email_format(email):
        return False, "Wrong Email Address Format"
    # Validate contact only if it's not empty
    if contact:
        if not contact_format(contact):
            return False, "Wrong Contact Number Format"
    else:
        contact = None  # Explicitly set as NULL for the database

    # Check uniqueness
    if User.query.filter_by(userId=id).first():
        return False, "ID already exists"
    if User.query.filter_by(userEmail=email).first():
        return False, "Email already exists"
    if contact and User.query.filter_by(userContact=contact).first():
        return False, "Contact number already exists"

    # Create staff object
    new_staff = User(
        userId=id,
        userDepartment=department_code,
        userName=name.upper(),
        userLevel=role,
        userEmail=email,
        userContact=contact,
        userGender=gender,
        userPassword=hashed_pw,
        userRegisterDateTime=datetime.now(timezone.utc),
        userCardId=cardId
    )

    db.session.add(new_staff)
    db.session.flush()  # Ensures userId is available for foreign keys

    matching_rows = TimetableRow.query.filter(
        func.replace(TimetableRow.lecturerName, " ", "") == func.replace(new_staff.userName, " ", "")
    ).all()

    if matching_rows:
        timetable = Timetable(user_id=new_staff.userId)
        db.session.add(timetable)
        db.session.flush()  # To get timetableId

        for row in matching_rows:
            row.timetable_id = timetable.timetableId

    if dept:
        if role == 2: # Dean
            dept.deanId = new_staff.userId
        elif role == 3: # HOS
            dept.hosId = new_staff.userId
        elif role == 4: # HOP
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



# -------------------------------
# Helper functions
# -------------------------------
def waiting_record(user_id):
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .filter(
            Exam.examStatus == True,
            InvigilatorAttendance.timeAction.is_(None),
            InvigilatorAttendance.invigilationStatus == False,
            InvigilatorAttendance.invigilatorId == user_id
        )
        .all()
    )

def confirm_record(user_id):
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
        .join(User, InvigilatorAttendance.invigilatorId == User.userId)
        .filter(InvigilatorAttendance.invigilatorId == user_id)
        .filter(InvigilatorAttendance.invigilationStatus == True)
    )

# cutoff_time = datetime.now() - timedelta(minutes=1)days=2
def open_record(user_id):
    cutoff_time = datetime.now() - timedelta(minutes=1)

    # Get current user's gender
    current_user = User.query.get(user_id)
    if not current_user:
        return []

    user_gender = current_user.userGender

    # Query open slots
    slots = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .outerjoin(User, InvigilatorAttendance.invigilatorId == User.userId)
        .filter(
            Exam.examStartTime > datetime.now(),
            InvigilatorAttendance.timeCreate < cutoff_time,
            InvigilatorAttendance.invigilationStatus == False,
            or_(
                InvigilatorAttendance.invigilatorId == None,  # unassigned
                User.userGender == user_gender               # same gender only
            )
        )
        .all()
    )

    # Remove duplicates by examId
    unique_slots = {}
    for slot in slots:
        exam_id = slot.report.examId
        if exam_id not in unique_slots:
            unique_slots[exam_id] = slot

    return list(unique_slots.values())


# -------------------------------
# Helper to get invigilator slot summary
# -------------------------------
def get_invigilator_slot_summary(user_id):
    waiting = waiting_record(user_id)
    confirmed = confirm_record(user_id).all()
    open_slots = open_record(user_id)

    return {
        "waiting_count": len(waiting),
        "confirmed_count": len(confirmed),
        "open_count": len(open_slots)
    }


# -------------------------------
# Email: Notify Invigilator About Slot Summary
# -------------------------------
def send_invigilator_slot_notification(user_id):
    user = User.query.get(user_id)
    if not user:
        return False, "User not found."

    # Get summary data
    summary = get_invigilator_slot_summary(user_id)
    waiting = summary["waiting_count"]
    confirmed = summary["confirmed_count"]
    open_count = summary["open_count"]

    try:
        msg = Message(
            'InvigilateX - Your Invigilation Slot Update',
            recipients=[user.userEmail]
        )

        msg.body = f'''Hi {user.userName},

You have new updates regarding your invigilation status.

Here is your current summary:

• Pending confirmation slots: {waiting}
• Confirmed upcoming slots: {confirmed}
• Open public slots available: {open_count}

If any action is needed from your side (accept / reject), please login to your InvigilateX portal.
'https://wm05.pythonanywhere.com/login'

Thank you,
The InvigilateX Team
'''

        mail.send(msg)
        return True, None
    
    except Exception as e:
        return False, f"Failed to send email. Error: {str(e)}"
