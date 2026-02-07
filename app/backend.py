import re
from flask_bcrypt import Bcrypt
from .database import *
from flask import redirect, url_for, flash, session
from flask_mail import Message
from flask import request
from user_agents import parse
from app import app, mail
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, exists, tuple_, func, select


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

# -------------------------------
# Basic User Details Function 5: Record every action taken
# -------------------------------
def record_action(action, target, targetId, userId):
    # Parse user-agent header to detect device and browser
    user_agent_str = request.headers.get('User-Agent', '')
    user_agent = parse(user_agent_str)

    # Get device info
    device = f"{user_agent.device.family} {user_agent.device.model or ''}".strip()
    # Get browser info
    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
    # Get IP address (consider reverse proxy headers if needed)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    new_action = Action(
        actionTake=action,
        actionTargetType=target,
        actionTargetId=targetId,
        actionBy=userId,
        actionDevice=device or 'UNKNOWN',
        actionIp=ip_address or '0.0.0.0',
        actionBrowser=browser or 'UNKNOWN',
        actionTime=datetime.now(timezone.utc)
    )

    # Save to database
    db.session.add(new_action)
    db.session.commit()
    return True


# Auth Function
# -------------------------------
# Auth Function 1: Check Login [Email and Password]
# -------------------------------
def check_login(loginEmail, loginPassword):
    user = User.query.filter_by(userEmail=loginEmail).first()
    if not user:
        return False, "Invalid Email or Password", None, None
    if not bcrypt.check_password_hash(user.userPassword, loginPassword):
        return False, "Invalid Password", None, None
    if user.userLevel not in ["ADMIN", "DEAN", "HOS", "HOP", "LECTURER", "PO"]:
        return False, "User Role is NotRecognized", None, None

    return True, user.userId, user.userLevel, user.userDepartment

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
def check_register(id, card, email, contact, password1=None, password2=None):
    # Email format
    if not email_format(email):
        return False, "Wrong Email Address Format"
    # Contact format
    if contact and not contact_format(contact):
        return False, "Wrong Contact Number Format"
    # Password match + format (only when provided)
    if password1 is not None and password2 is not None:
        if password1 != password2:
            return False, "Passwords Do Not Match"
        if not password_format(password1):
            return False, "Wrong Password Format"

    # Uniqueness checks
    if User.query.filter_by(userId=id).first():
        return False, "ID Already Exists"
    if User.query.filter_by(userEmail=email).first():
        return False, "Email Already Exists"
    if contact and User.query.filter_by(userContact=contact).first():
        return False, "Contact Number Already Exists"
    if card and User.query.filter_by(userCardId=card).first():
        return False, "Card ID Already Exists"
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
        msg.body = f'''Hi {user.userName},

We received a request to reset your password for your InvigilateX account.

To reset your password, please click the link below:
{reset_link}

If you did not request this change, please ignore this email.

Thank you,  
The InvigilateX Team'''
        
        mail.send(msg)
        record_action("REQUEST RESET PASSWORD", "FORGOT PASSWORD", user.userId, user.userId)
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
        msg.body = f'''Hi {user.userName},

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

    record_action("RESET PASSWORD SUCCESSFUL", "RESET PASSWORD", user.userId, user.userId)
    user.userPassword = bcrypt.generate_password_hash(resetPassword1).decode('utf-8')
    user.isLocked = False             # ✅ unlock the account
    user.failedAttempts = 0           # ✅ reset counter
    db.session.commit()
    return user, None


# Admin Function
# -------------------------------
# Admin Function 1: Create Course with Automatically Exam when with all correct data
# -------------------------------
def create_course_and_exam(userid, department, code, section, name, hour, students, intake):
    # Validate department code
    department_name = Department.query.filter_by(departmentCode=department.upper() if department else None).first()
    if not department_name:
        department = None
    else:
        department = department.upper()

    # Validate courseCodeSection
    courseCodeSection_text = f"{intake}/{code}/{section}".upper() if code and section else None
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

    exam_id = None
    new_exam = Exam(
        examOutput=None
    )
    db.session.add(new_exam)
    db.session.flush()  # Get the examId before commit
    exam_id = new_exam.examId

    # Create the new Course
    new_course = Course(
        courseCodeSectionIntake=courseCodeSection_text,
        courseDepartment=department,
        courseName=name.upper(),
        courseHour=hour,
        courseStudent=students,
        courseExamId=exam_id,
        courseStatus=True
    )
    db.session.add(new_course)
    db.session.commit()
    record_action("UPLOAD/ADD NEW COURSE", "COURSE", courseCodeSection_text, userid)
    return True, f"Course [{courseCodeSection_text} - {name.upper()}] created successfully"


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
        except Exception:
            continue

    return True

from datetime import timedelta

# -------------------------------
# Admin Function 2: Fill in Exam details and Automatically VenueExam, InvigilationReport, InvigilatorAttendance
# -------------------------------
from datetime import timedelta

def create_exam_and_related(user, start_dt, end_dt, courseSection, venue_list, studentPerVenue_list, open, close):
    # --- Fetch course & exam ---
    course = Course.query.filter_by(courseCodeSectionIntake=courseSection).first()
    if not course:
        return False, f"No course found for {courseSection}"

    exam = course.exam
    if not exam:
        return False, f"Exam for course {courseSection} not found"

    # --- Prevent duplicate assignment ---
    existing_sessions = VenueSession.query.join(VenueExam, VenueExam.venueSessionId == VenueSession.venueSessionId).filter(VenueExam.examId == exam.examId).first()
    if existing_sessions:
        return False, f"Exam {courseSection} already has assigned invigilators/venues"

    # --- Exclude course staff from invigilators ---
    exclude_ids = [uid for uid in (course.coursePractical, course.courseTutorial, course.courseLecturer) if uid]

    # --- Adjust end datetime if end < start ---
    adj_end_dt = end_dt if end_dt > start_dt else end_dt + timedelta(days=1)
    duration_hours = (adj_end_dt - start_dt).total_seconds() / 3600.0

    # --- Eligible invigilators ---
    base_query = User.query.filter(User.userLevel == "LECTURER", User.userStatus == True)
    if exclude_ids:
        base_query = base_query.filter(~User.userId.in_(exclude_ids))

    flexible = []
    not_flexible = []

    for inv in base_query.all():
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
    male_pool = sorted(
        [i for i in eligible_invigilators if i.userGender is True],
        key=lambda x: (x.userCumulativeHours or 0) + (x.userPendingCumulativeHours or 0)
    )
    female_pool = sorted(
        [i for i in eligible_invigilators if i.userGender is False],
        key=lambda x: (x.userCumulativeHours or 0) + (x.userPendingCumulativeHours or 0)
    )

    # --- Store summary for reporting ---
    not_flex_ids = [str(i.userId) for i, t, a in not_flexible]
    exam.examOutput = [base_query.count(), len(eligible_invigilators), len(flexible), len(not_flexible), not_flex_ids, len(male_pool), len(female_pool)]
    db.session.add(exam)

    # --- Require at least 1 male and 1 female ---
    if not male_pool or not female_pool:
        return False, "Need at least one Male and one Female invigilator"

    # --- Assign invigilators to venues ---
    for venue_text, spv in zip(venue_list, studentPerVenue_list):
        spv = int(spv)
        venue_text = venue_text.strip().upper()
        venue = Venue.query.filter_by(venueNumber=venue_text).first()
        if not venue:
            continue  # skip missing venue

        assigned_students = min(spv, venue.venueCapacity)
        required_invigilators = 3 if assigned_students > 32 else 2

        # Reuse existing VenueSession if exists
        session = VenueSession.query.filter_by(
            venueNumber=venue.venueNumber,
            startDateTime=start_dt,
            endDateTime=end_dt
        ).first()

        if not session:
            session = VenueSession(
                venueNumber=venue.venueNumber,
                startDateTime=start_dt,
                endDateTime=end_dt,
                backupInvigilatorId=None,
                noInvigilator=required_invigilators
            )
            db.session.add(session)
            db.session.flush()  # to get session ID

        # Create VenueExam
        venue_exam = VenueExam(
            examId=exam.examId,
            venueSessionId=session.venueSessionId,
            studentCount=assigned_students
        )
        db.session.add(venue_exam)
        # --- Pick invigilators ---
        chosen = []

        # Always pick at least 1 male and 1 female if available
        if male_pool:
            chosen.append(male_pool.pop(0))
        if female_pool:
            chosen.append(female_pool.pop(0))

        # Pick 3rd invigilator if required
        if required_invigilators == 3:
            candidate = None
            if male_pool and female_pool:
                # Pick who has higher cumulative hours
                candidate = male_pool[0] if (male_pool[0].userCumulativeHours or 0) > (female_pool[0].userCumulativeHours or 0) else female_pool[0]
            elif male_pool:
                candidate = male_pool[0]
            elif female_pool:
                candidate = female_pool[0]

            if candidate:
                chosen.append(candidate)
                if candidate in male_pool: male_pool.remove(candidate)
                if candidate in female_pool: female_pool.remove(candidate)

        # --- Assign chosen invigilators ---
        existing_invigilators = {v.invigilatorId for v in session.invigilators}
        for inv in chosen:
            if inv.userId in existing_invigilators:
                continue  # skip duplicates
            inv.userPendingCumulativeHours = (inv.userPendingCumulativeHours or 0.0) + duration_hours
            db.session.add(VenueSessionInvigilator(
                venueSessionId=session.venueSessionId,
                invigilatorId=inv.userId,
                timeCreate=open,
                timeExpire=close
            ))

    db.session.commit()
    record_action("UPLOAD NEW EXAM", "EXAM", exam.examId, user)
    return True, f"Exam scheduled successfully for {courseSection}"


# -------------------------------
# Adjust invigilators based on venue & capacity
# -------------------------------
def recalc_invigilators_for_new_exams():
    # Get all venue sessions that have exams
    sessions = (db.session.query(VenueSession).join(VenueSession.exams).all())
    for session in sessions:
        start_dt = session.startDateTime
        end_dt = session.endDateTime

        # Total students in this venue session
        total_students = sum(ve.studentCount for ve in session.exams)
        # Required invigilators
        required_invigilators = 3 if total_students > 32 else 2
        # Current invigilators assigned to this session
        current_assignments = session.invigilators
        # Sort invigilators by total workload
        sorted_assignments = sorted(
            current_assignments,
            key=lambda vsi: (
                (vsi.invigilator.userCumulativeHours or 0.0) +
                (vsi.invigilator.userPendingCumulativeHours or 0.0)
            )
        )

        # Remove excess invigilators
        duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
        to_remove = sorted_assignments[required_invigilators:]

        for vsi in to_remove:
            inv = vsi.invigilator
            if inv:
                inv.userPendingCumulativeHours = max(0.0, (inv.userPendingCumulativeHours or 0.0) - duration_hours)
            db.session.delete(vsi)
        db.session.flush()

        # Update examNoInvigilator for each exam in this session
        for ve in session.exams:
            exam = ve.exam
            # exam.examNoInvigilator = len(session.invigilators)
    db.session.commit()


# -------------------------------
# Admin Function 3: Create Staff when with all correct data
# -------------------------------
def create_staff(userId, id, department, name, role, email, contact, gender, hashed_pw, cardId):
    # Call shared validation logic here
    valid, message = check_register(id, cardId, email, contact)
    if not valid:
        return False, message

    # Normalize department code
    department_code = department.upper() if department else None
    dept = Department.query.filter_by(departmentCode=department_code).first()
    if not dept:
        department_code = None

    cardId = cardId if cardId else None
    contact = contact if contact else None

    # Create staff object after validation passes
    new_staff = User(
        userId=id,
        userDepartment=department_code,
        userName=name.upper(),
        userLevel=role,
        userEmail=email,
        userContact=contact,
        userGender=gender,
        userPassword=hashed_pw,
        userCardId=cardId,
        userStatus=1
    )

    db.session.add(new_staff)
    db.session.flush()

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
        if role == "DEAN":
            dept.deanId = new_staff.userId
        elif role == "HOS":
            dept.hosId = new_staff.userId
        elif role == "HOP":
            dept.hopId = new_staff.userId
        db.session.add(dept)

    db.session.commit()
    record_action("UPLOAD/ADD STAFF", "STAFF", id, userId)
    return True, f"Staff [{id} - {name.upper()}] created successfully"


# -------------------------------
# Admin Function 5: View and Edit Admin Profile
# -------------------------------
def check_profile(user_id, cardId, contact, password1, password2):
    user_record = User.query.filter_by(userId=user_id).first()
    if not user_record:
        return False, "User not found"

    if cardId:
        # Check if cardId exists for other users
        existing_card = User.query.filter(User.userCardId == cardId, User.userId != user_id).first()
        if existing_card:
            return False, "Card ID Already Exists"

    if contact:
        # Validate format
        if not contact_format(contact):
            return False, "Wrong Contact Number Format"
        # Check uniqueness (excluding current user)
        if contact != (user_record.userContact or ''):
            is_unique, msg = check_contact(contact)
            if not is_unique:
                return False, msg

    if password1 or password2:
        if not password1 or not password2:
            return False, "Both Password Fields Are Required"
        if not password_format(password1) or not password_format(password2):
            return False, "Wrong Password Format"
        if password1 != password2:
            return False, "Passwords Do Not Match"

    if not cardId and not contact and not password1 and not password2:
        return True, "No Update"

    return True, ""




# -------------------------------
# HELPER 1: Waiting Slots
# -------------------------------
def waiting_record(user_id):
    current_time = datetime.now() + timedelta(hours=8)
    
    rejected_subq = (
        InvigilatorAttendance.query
        .filter(
            InvigilatorAttendance.invigilatorId == user_id,
            InvigilatorAttendance.rejectReason.isnot(None)
        )
        .with_entities(InvigilatorAttendance.reportId)
        .subquery()
    )
    
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .filter(
            InvigilatorAttendance.invigilatorId == user_id,
            InvigilatorAttendance.invigilationStatus == False,
            InvigilatorAttendance.rejectReason.is_(None),
            InvigilatorAttendance.timeAction.is_(None),
            InvigilatorAttendance.timeCreate <= current_time,
            ~InvigilatorAttendance.reportId.in_(select(rejected_subq))
        )
        .all()
    )


# -------------------------------
# HELPER 2: Confirmed Slots
# -------------------------------
def confirm_record(user_id):
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
        .filter(
            InvigilatorAttendance.invigilatorId == user_id,
            InvigilatorAttendance.invigilationStatus == True,
        )
        .all()
    )

def reject_record(user_id):
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
        .join(User, InvigilatorAttendance.invigilatorId == User.userId)
        .filter(
            InvigilatorAttendance.invigilatorId == user_id,
            InvigilatorAttendance.rejectReason.isnot(None)  # only rejected rows
        )
        .all()
    )


# -------------------------------
# HELPER 3: Open Slots
# -------------------------------
def open_record(user_id):
    current_time = datetime.now() + timedelta(hours=8)

    user = User.query.get(user_id)
    if not user:
        return []

    user_gender = user.userGender

    # Subquery: Exams the user previously rejected
    rejected_exam_subq = (
        db.session.query(InvigilationReport.examId)
        .join(InvigilatorAttendance, InvigilationReport.invigilationReportId == InvigilatorAttendance.reportId)
        .filter(
            InvigilatorAttendance.invigilatorId == user_id,
            InvigilatorAttendance.rejectReason.isnot(None)
        )
        .distinct()
        .subquery()
    )

    # Fetch all open slots matching gender and not rejected
    slots = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .filter(
            InvigilatorAttendance.invigilationStatus == False,
            InvigilatorAttendance.rejectReason.is_(None),
            InvigilatorAttendance.timeExpire <= current_time,
            InvigilatorAttendance.invigilator.has(userGender=user_gender),
            ~InvigilationReport.examId.in_(select(rejected_exam_subq))
        )
        .all()
    )

    # Fetch all accepted slots for the user to check conflicts
    assigned_slots = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilationReport.invigilationReportId == InvigilatorAttendance.reportId)
        .join(Exam, Exam.examId == InvigilationReport.examId)
        .filter(
            InvigilatorAttendance.invigilatorId == user_id,
            InvigilatorAttendance.invigilationStatus == True
        )
        .all()
    )

    def is_overlap(start1, end1, start2, end2):
        return max(start1, start2) < min(end1, end2)

    unique_slots = {}
    for slot in slots:
        exam = slot.report.exam
        slot_start, slot_end = exam.examStartTime, exam.examEndTime
        if slot_end < slot_start:
            slot_end += timedelta(days=1)

        # Skip slot if it conflicts with any assigned slot
        conflict = False
        for assigned in assigned_slots:
            assigned_exam = assigned.report.exam
            assigned_start, assigned_end = assigned_exam.examStartTime, assigned_exam.examEndTime
            if assigned_end < assigned_start:
                assigned_end += timedelta(days=1)
            if is_overlap(slot_start, slot_end, assigned_start, assigned_end):
                conflict = True
                break
        if conflict:
            continue  # Skip conflicting slot

        # Deduplicate by examId
        if exam.examId not in unique_slots:
            unique_slots[exam.examId] = slot

    return list(unique_slots.values())



# -------------------------------
# Helper: Slot Summary
# -------------------------------
def get_invigilator_slot_summary(user_id):
    waiting = waiting_record(user_id)
    confirmed = confirm_record(user_id)
    open_slots = open_record(user_id)
    open_times = [slot.timeExpire.strftime("%Y-%m-%d %H:%M:%S") for slot in waiting]

    return {
        "waiting_count": len(waiting),
        "confirmed_count": len(confirmed),
        "open_slots": open_slots,
        "open_times": open_times
    }


# -------------------------------
# Build exam block for email
# -------------------------------
def build_exam_block(exams):
    lines = []
    for attendance in exams:
        course = Course.query.filter_by(courseExamId=attendance.report.examId).first()
        exam = Exam.query.get(attendance.report.examId)
        lines.append(
            f"Course : {course.courseName} ({course.courseCode})\n"
            f"Venue  : {attendance.venueNumber}\n"
            f"Date   : {exam.examStartTime.strftime('%d %b %Y, %I:%M %p')}\n"
        )
    return "\n".join(lines) if lines else "None"


# -------------------------------
# Email: Notify Invigilator
# -------------------------------
def send_invigilator_slot_notifications_for_all():
    now = datetime.now() + timedelta(hours=8)
    users = User.query.join(InvigilatorAttendance, User.userId == InvigilatorAttendance.invigilatorId).distinct().all()
    results = []

    for user in users:
        summary = get_invigilator_slot_summary(user.userId)

        # Expiring tomorrow
        expiring = (
            InvigilatorAttendance.query
            .filter(
                InvigilatorAttendance.invigilatorId == user.userId,
                InvigilatorAttendance.invigilationStatus == False,
                InvigilatorAttendance.rejectReason.is_(None),
                func.date(InvigilatorAttendance.timeExpire) == (now + timedelta(days=1)).date()
            )
            .all()
        )

        # Confirmed exams tomorrow
        confirmed_tomorrow = (
            InvigilatorAttendance.query
            .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
            .join(Exam, InvigilationReport.examId == Exam.examId)
            .filter(
                InvigilatorAttendance.invigilatorId == user.userId,
                InvigilatorAttendance.invigilationStatus == True,
                Exam.examStartTime.between(now + timedelta(days=1), now + timedelta(days=2))
            )
            .all()
        )

        # Skip if nothing to notify
        if summary["waiting_count"] == 0 and not summary["open_slots"] and not expiring and not confirmed_tomorrow:
            continue

        exam_block = build_exam_block(confirmed_tomorrow)

        expiry_notice = ""
        if expiring:
            expiry_notice = f"⚠️ You have {len(expiring)} slot(s) to accept or reject expiring tomorrow.\n"

        msg = Message(
            "InvigilateX – Slot Notification",
            recipients=[user.userEmail]
        )

        msg.body = f"""Hi {user.userName},

📌 Slot Summary
• Waiting slots       : {summary['waiting_count']}
• Confirmed slots  : {summary['confirmed_count']}
• Open slots          : {', '.join(summary['open_times']) if summary['open_times'] else 'None'}

{expiry_notice}

📅 Tomorrow's Exams
{exam_block}

Please login to InvigilateX to check your invigilation slot(s):
https://wm05.pythonanywhere.com/login

Reminder:
Please make sure to check in 30 minutes earlier before the commencement of the exam at the Exam Office. 

Thank you,
InvigilateX System
"""
        try:
            mail.send(msg)
            results.append((user.userId, "sent"))
        except Exception as e:
            results.append((user.userId, f"failed: {str(e)}"))

    return results

