
from datetime import datetime, timedelta, timezone
from flask import render_template, request, redirect, url_for, flash, session, get_flashed_messages, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from app import app
from .backend import *
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()


# -------------------------------
# Function for default route 
# -------------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))


# -------------------------------
# Function for Auth Login route
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    # cleanup_expired_timetable_rows()
    update_attendanceStatus()
    login_text = ''
    password_text = ''

    if request.method == 'POST':
        login_text = request.form.get('login_field', '').strip()
        password_text = request.form.get('password_field', '').strip()
        
        valid, result, role = check_login(login_text, password_text)
        if not valid:
            flash(result, 'login_error')
            all_messages = get_flashed_messages(with_categories=True)
            return render_template('auth/login.html', login_text=login_text, password_text=password_text, all_messages=all_messages)

        session['user_id'] = result
        session['user_role'] = role

        if role == ADMIN:
            return redirect(url_for('admin_homepage'))
        elif role in (DEAN, HOS, HOP, LECTURER):
            return redirect(url_for('user_homepage'))
        else:
            flash("Unknown role", "login_error")
            return redirect(url_for('login'))

    # Ensure GET request also includes flashed messages
    all_messages = get_flashed_messages(with_categories=True)
    return render_template('auth/login.html', login_text=login_text, password_text=password_text, all_messages=all_messages)


# -------------------------------
# Function for Auth Register route
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    role_map = {
        'LECTURER': LECTURER,
        'DEAN': DEAN,
        'HOS': HOS,
        'HOP': HOP,
        'ADMIN': ADMIN
    }
    
    department_data = Department.query.all()
    id_text = ''
    name_text = ''
    email_text = ''
    contact_text = ''
    department_text = ''
    role_text = ''
    gender_text = ''
    password1_text = ''
    password2_text = ''
    error_message = None

    if request.method == 'POST':
        id_text = request.form.get('userid', '').strip()
        name_text = request.form.get('username', '').strip()
        email_text = request.form.get('email', '').strip()
        contact_text = request.form.get('contact', '').strip()
        department_text = request.form.get('department', '').strip()
        role_text = request.form.get('role', '').strip()
        gender_text = request.form.get('gender', '').strip()
        password1_text = request.form.get('password1', '').strip()
        password2_text = request.form.get('password2', '').strip()

        is_valid, error_message = check_register(id_text, email_text, contact_text, password1_text, password2_text)

        if error_message:
            flash(error_message, 'error')
        elif is_valid:
            hashed_pw = bcrypt.generate_password_hash(password1_text).decode('utf-8')
            new_user = User(
                userId=id_text.upper(),
                userName=name_text.upper(),
                userDepartment=department_text.upper(),
                userLevel=role_map.get(role_text, ADMIN),  # default to ADMIN if role missing
                userEmail=email_text,
                userContact=contact_text,
                userPassword=hashed_pw,
                userGender=gender_text,
                userStatus=0,  # not verified yet
                userRegisterDateTime=datetime.now()
            )
            db.session.add(new_user)
            db.session.commit()

            # Send verification email after saving user
            success, message = send_verifyActivateLink(email_text)
            if success:
                flash("Verify link sent to your email address.", 'success')
            else:
                flash(f"Failed to send verification email: {message}", 'error')

            flash("Register successful! Log in with your registered email address.", "success")
            return redirect(url_for('login'))

    return render_template('auth/register.html', id_text=id_text, name_text=name_text, email_text=email_text,
                           contact_text=contact_text, password1_text=password1_text, password2_text=password2_text, gender_text=gender_text,
                           department_text=department_text, role_text=role_text, department_data=department_data, error_message=error_message)


@app.route('/verify/<token>')
def verifyAccount(token):
    try:
        email = serializer.loads(token, salt='account-verify-salt', max_age=3600)
        user = User.query.filter_by(userEmail=email).first()
        if not user:
            flash("Invalid verification link.", "danger")
            return redirect(url_for('login'))

        user.userStatus = True
        db.session.commit()
        flash("Your account has been verified successfully!", "success")
        return redirect(url_for('login'))

    except SignatureExpired:
        flash("The verification link has expired.", "warning")
        return redirect(url_for('register'))
    except BadSignature:
        flash("Invalid verification token.", "danger")
        return redirect(url_for('register'))


# -------------------------------
# Function for Auth ForgotPassword route
# -------------------------------
@app.route('/forgotPassword', methods=['GET', 'POST'])
def forgotPassword():
    forgot_email_text = ''
    error_message = None

    if request.method == 'POST':
        forgot_email_text = request.form.get('email', '').strip()

        # Validate and send reset email
        success, message = check_forgotPasswordEmail(forgot_email_text)
        if not success:
            error_message = message
            flash(str(error_message), 'error')
        else:
            flash("Reset link sent to your email address.", 'success')
            return redirect(url_for('login'))

    return render_template('auth/forgotPassword.html', forgot_email_text=forgot_email_text, error_message=error_message)


# -------------------------------
# Function for Auth ResetPassword route
# -------------------------------
@app.route('/resetPassword/<token>', methods=['GET', 'POST'])
def resetPassword(token):
    password_text_1 = ''
    password_text_2 = ''
    error_message = role_required

    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '').strip()
        password_text_2 = request.form.get('password2', '').strip()

        user, error_message = check_resetPassword(token, password_text_1, password_text_2)
        if error_message:
            flash(error_message, 'error')
        elif user:
            flash("Password reset successful! Log in with your new password.", "success")
            return redirect(url_for('login'))

    return render_template('auth/resetPassword.html', password_text_1=password_text_1, password_text_2=password_text_2, error_message=error_message)


# -------------------------------
# Function for Auth Logout route
# -------------------------------
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login')) 


# -------------------------------
# Function for Auth SaveLoginCredentials 
# -------------------------------
@app.context_processor
def inject_user_data():
    userId = session.get('user_id')
    if userId:
        user = User.query.get(userId)
        if user:
            return {
                'user_id': userId,
                'user_name': user.userName,
                'user_department': user.userDepartment,
                'user_level': user.userLevel,
                'user_email': user.userEmail,
                'user_contact': user.userContact,
                'user_password': user.userPassword,
                'user_status': user.userStatus,
                'user_invigilationHour': user.userCumulativeHours,
                'user_pendingInvigilationHour': user.userPendingCumulativeHours
            }
    return {
        'user_id': None,
        'user_name': '',
        'user_department': '',
        'user_level': '',
        'user_email': '',
        'user_contact': '',
        'user_password': '',
        'user_status': '',
        'user_invigilationHour': '',
        'user_pendingInvigilationHour': ''
    }


# -------------------------------
# Function for Auth RequiredLoginForEachPage
# -------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Check if logged in
        if 'user_id' not in session:
            flash("Please log in first", "error")
            return redirect(url_for("login"))

        # 2. Get user from database
        user = User.query.get(session['user_id'])
        if not user:
            flash("User not found", "error")
            return redirect(url_for("login"))

        # 3. Check status
        if user.userStatus == 0:
            flash("Please activate your account using the link in your email.", "error")
            return redirect(url_for("login"))
        elif user.userStatus == 2:
            flash("This account has been deleted. Please contact support.", "error")
            return redirect(url_for("login"))

        # 4. Correct status allow in
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------
# Function for Admin Homepage route
# -------------------------------
@app.route('/admin/home', methods=['GET', 'POST'])
@login_required
def admin_homepage():
    return render_template('admin/adminHomepage.html', active_tab='admin_hometab')


# -------------------------------
# Helper functions
# -------------------------------
def waiting_record(user_id):
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .filter(
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
        .filter(InvigilatorAttendance.timeAction.is_(None))
    )

# cutoff_time = datetime.now() - timedelta(minutes=1)days=2
def open_record():
    cutoff_time = datetime.now() - timedelta(minutes=1)

    slots = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
        .join(User, InvigilatorAttendance.invigilatorId == User.userId)
        .filter(
            InvigilatorAttendance.invigilationStatus == False,
            InvigilatorAttendance.timeCreate < cutoff_time,
            Exam.examStartTime > datetime.now()
        )
        .all()
    )

    # Remove duplicates by examId (keep first)
    unique_slots = {}
    for slot in slots:
        exam_id = slot.report.examId
        if exam_id not in unique_slots:
            unique_slots[exam_id] = slot

    return list(unique_slots.values())


# -------------------------------
# Main User Homepage
# -------------------------------
@app.route('/user/home', methods=['GET', 'POST'])
@login_required
def user_homepage():
    user_id = session.get('user_id')
    chosen = User.query.filter_by(userId=user_id).first()
    waiting = waiting_record(user_id)
    confirm = confirm_record(user_id).filter(Exam.examEndTime > datetime.now()).all()

    # Get open slots + gender filter
    open_slots = open_record()
    if chosen:
        open_slots = [slot for slot in open_slots if slot.invigilator.userGender == chosen.userGender]

    if request.method == 'POST':
        action = request.form.get('action')

        # Handle waiting approval
        waiting_id = request.form.get('w_id')
        waiting_slot = InvigilatorAttendance.query.filter_by(
            invigilatorId=user_id,
            attendanceId=waiting_id
        ).first()

        if waiting_slot:
            exam = (
                Exam.query
                .join(InvigilationReport, Exam.examId == InvigilationReport.examId)
                .filter(InvigilationReport.invigilationReportId == waiting_slot.reportId)
                .first()
            )

            pending_hours = 0
            if exam and exam.examStartTime and exam.examEndTime:
                start_dt, end_dt = exam.examStartTime, exam.examEndTime
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                pending_hours = (end_dt - start_dt).total_seconds() / 3600.0

            if action == 'accept':
                waiting_slot.invigilationStatus = True
                waiting_slot.timeAction = datetime.now()

            elif action == 'reject':
                chosen.userPendingCumulativeHours = max((chosen.userPendingCumulativeHours or 0) - pending_hours, 0)
                waiting_slot.invigilationStatus = False

            waiting_slot.timeAction = datetime.now()
            db.session.commit()

        # Handle open slot accept
        open_id = request.form.get('a_id')
        open_slot = InvigilatorAttendance.query.filter_by(attendanceId=open_id).first()

        if open_slot and action == 'open_accept' and chosen:
            exam = (
                Exam.query
                .join(InvigilationReport, Exam.examId == InvigilationReport.examId)
                .filter(InvigilationReport.invigilationReportId == open_slot.reportId)
                .first()
            )

            # Gender check here (must match user)
            if open_slot.invigilator.userGender != chosen.userGender:
                flash("Cannot accept: slot reserved for same-gender invigilators only.", "error")
                return redirect(url_for('user_homepage'))

            # Assign slot
            open_slot.invigilatorId = user_id
            open_slot.invigilationStatus = True
            open_slot.timeAction = datetime.now()

            # Update hours
            hours = 0
            if exam and exam.examStartTime and exam.examEndTime:
                start_dt, end_dt = exam.examStartTime, exam.examEndTime
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                hours = (end_dt - start_dt).total_seconds() / 3600.0

            chosen.userPendingCumulativeHours  = (chosen.userPendingCumulativeHours or 0) + hours
            db.session.commit()
            flash("Open Slot Accepted Successfully", "success")
        return redirect(url_for('user_homepage'))
    return render_template('user/userHomepage.html', active_tab='user_hometab', waiting=waiting, confirm=confirm, open=open_slots)





# -------------------------------
# Helper functions
# -------------------------------
def hours_diff(start, end):
    """Calculate hours difference between two naive datetimes."""
    if not start or not end:
        return 0
    return max(0, (end - start).total_seconds() / 3600.0)

# -------------------------------
# Attendance route
# -------------------------------
@app.route('/attendance', methods=['GET', 'POST'])
def attendance_record():
    if request.method == 'POST':
        try:
            data = request.get_json()
            card_input = data.get('cardNumber', '').strip()
            if not card_input:
                return jsonify({"success": False, "message": "Card scan missing!"})

            # Find user by card
            user = User.query.filter_by(userCardId=card_input).first()
            if not user:
                return jsonify({"success": False, "message": "Card not recognized!"})

            user_id = user.userId

            # Get all assigned time slots for this user
            timeSlots = InvigilatorAttendance.query.filter_by(invigilatorId=user_id).all()
            if not timeSlots:
                return jsonify({"success": False, "message": "No exam assigned!"})

            # Capture device time shifted to Malaysia Time (+8 hours)
            scan_time = datetime.utcnow() + timedelta(hours=8)

            # Find nearest exam session by time proximity
            def exam_proximity(att):
                exam = getattr(att.report, "exam", None)
                if not exam:
                    return float("inf")
                start, end = exam.examStartTime, exam.examEndTime
                if not start or not end:
                    return float("inf")
                return min(abs((start - scan_time).total_seconds()), abs((end - scan_time).total_seconds()))

            timeSlots_sorted = sorted(timeSlots, key=exam_proximity)
            confirm = timeSlots_sorted[0]

            exam = getattr(confirm.report, "exam", None)
            if not exam or not exam.examStartTime or not exam.examEndTime:
                return jsonify({"success": False, "message": "Exam details missing!"})

            start, end = exam.examStartTime, exam.examEndTime

            # Define check-in and check-out windows
            checkin_start = start - timedelta(hours=1)   # 1 hour before exam
            checkin_end = end                             # until exam end
            checkout_start = end                          # check-out starts at exam end
            checkout_end = end + timedelta(hours=1)       # optional buffer after exam
            checkout_auto = end + timedelta(hours=1)      # auto check-out if missed

            # Update attendance
            for att in timeSlots:
                report = getattr(att, "report", None)
                exam = getattr(report, "exam", None)
                if not exam or not exam.examStartTime or not exam.examEndTime:
                    continue

                start, end = exam.examStartTime, exam.examEndTime
                checkin_start, checkin_end = start - timedelta(hours=1), end
                checkout_start, checkout_end = end, end + timedelta(hours=1)
                checkout_auto = end + timedelta(hours=1)

                # --- Check-in logic ---
                if not att.checkIn:
                    if checkin_start <= scan_time <= start:
                        att.checkIn = scan_time
                        att.remark = "CHECK IN"
                    elif start < scan_time <= checkin_end:
                        att.checkIn = scan_time
                        att.remark = "CHECK IN LATE"

                # --- Check-out logic ---
                elif not att.checkOut:
                    if checkout_start <= scan_time <= checkout_end:
                        att.checkOut = scan_time
                        att.remark = "COMPLETED"
                    elif scan_time < end:
                        att.checkOut = scan_time
                        att.remark = "CHECK OUT EARLY"

                # --- Auto check-out if missed ---
                if not att.checkOut and scan_time > checkout_auto:
                    att.checkOut = checkout_auto
                    att.remark = "COMPLETED"

                # --- Update user cumulative hours ---
                if att.checkIn and att.checkOut:
                    exam_hours = hours_diff(start, end)
                    actual_hours = hours_diff(att.checkIn, att.checkOut)
                    if att.checkIn > start or att.checkOut < end:
                        user.userCumulativeHours = user.userCumulativeHours - exam_hours + actual_hours
                    att.invigilationStatus = True

                # Record the action time
                att.timeAction = scan_time

            db.session.commit()

            # Prepare response safely
            report = getattr(confirm, "report", None)
            exam = getattr(report, "exam", None)
            course = getattr(exam, "course", None)
            venues = []
            if exam and getattr(exam, "venue_availabilities", None):
                venues = [v.venueNumber for v in exam.venue_availabilities]
            venue_list = ", ".join(venues) if venues else "N/A"

            response_data = {
                "courseName": getattr(course, "courseName", "N/A"),
                "courseCode": getattr(course, "courseCodeSectionIntake", "N/A"),
                "students": getattr(course, "courseStudent", "N/A"),
                "examStart": exam.examStartTime.strftime("%d/%b/%Y %H:%M") if exam else "N/A",
                "examEnd": exam.examEndTime.strftime("%d/%b/%Y %H:%M") if exam else "N/A",
                "checkIn": confirm.checkIn.strftime("%d/%b/%Y %H:%M:%S") if confirm.checkIn else "None",
                "checkOut": confirm.checkOut.strftime("%d/%b/%Y %H:%M:%S") if confirm.checkOut else "None",
                "remark": confirm.remark or "",
                "examVenue": venue_list
            }

            return jsonify({"success": True, "data": response_data})

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Attendance record failed: {e}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"})

    # GET request: render attendance page
    return render_template('auth/attendance.html')










def parse_date_range(date_range):
    """Parse classWeekDate 'MM/DD/YYYY-MM/DD/YYYY' and return (start, end) datetime safely."""
    if not date_range:
        return None, None
    try:
        # Split only on the last hyphen in case there are others in the string
        start_str, end_str = date_range.rsplit("-", 1)
        start = datetime.strptime(start_str.strip(), "%m/%d/%Y")
        end = datetime.strptime(end_str.strip(), "%m/%d/%Y")
        return start, end
    except Exception as e:
        print(f"Date parse error for '{date_range}': {e}")
        return None, None


# -------------------------------
# Function run non-stop
# -------------------------------
def cleanup_expired_timetable_rows():
    """Delete timetable rows whose classWeekDate end date has expired."""
    now = datetime.now()
    all_rows = TimetableRow.query.all()

    for row in all_rows:
        if not row.classWeekDate:
            continue

        start, end = parse_date_range(row.classWeekDate)
        if end is None:
            continue  # Skip malformed rows

        if now > end:
            db.session.delete(row)

    db.session.commit()  # Commit even if 0, or you can add a check


def update_attendanceStatus():
    all_attendance = InvigilatorAttendance.query.all()
    timeNow = datetime.now()

    for attendance in all_attendance:
        report = attendance.report
        exam = report.exam if report else None
        if not exam:
            continue

        check_in = attendance.checkIn
        check_out = attendance.checkOut

        exam_start = exam.examStartTime
        exam_end = exam.examEndTime

        remark = "PENDING"

        # -----------------------------
        # 1️⃣ Handle missing check-out after 30 minutes of exam end
        # -----------------------------
        if check_in and not check_out and timeNow > exam_end + timedelta(minutes=30):
            attendance.checkOut = exam_end + timedelta(minutes=30)
            check_out = attendance.checkOut

        # -----------------------------
        # 2️⃣ Determine remark logic
        # -----------------------------
        if not check_in and not check_out:
            remark = "PENDING"

        elif check_in and not check_out:
            # Checked in but never checked out (still before auto-assign threshold)
            if timeNow <= exam_end + timedelta(minutes=30):
                remark = "ONGOING"
            else:
                remark = "EXPIRED"

        elif check_in and check_out:
            # Check-in & Check-out both exist — evaluate timing
            if check_in <= exam_start and check_out >= exam_end:
                remark = "COMPLETED"
            elif check_in > exam_start and check_out >= exam_end:
                remark = "CHECK IN LATE"
            elif check_in <= exam_start and check_out < exam_end:
                remark = "CHECK OUT EARLY"
            elif check_in > exam_start and check_out < exam_end:
                remark = "CHECK IN LATE & CHECK OUT EARLY"
            else:
                remark = "COMPLETED"

        # -----------------------------
        # 3️⃣ Auto-expire logic (after exam + 30min)
        # -----------------------------
        if timeNow > exam_end + timedelta(minutes=30):
            if not check_in and not check_out:
                remark = "EXPIRED"

        attendance.remark = remark

    db.session.commit()






