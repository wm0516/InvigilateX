from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session, get_flashed_messages, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_bcrypt import Bcrypt
import threading
import time
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
    update_exam_status()
    update_attendanceStatus()
    login_text = ''
    password_text = ''

    if request.method == 'POST':
        login_text = request.form.get('login_field', '').strip()
        password_text = request.form.get('password_field', '').strip()

        user = User.query.filter_by(userEmail=login_text).first()
        if user:
            # Check if account is locked
            if user.isLocked:
                flash("⚠️ Your account is locked. Please check your email for the reset password link.", "login_error")
                all_messages = get_flashed_messages(with_categories=True)
                return render_template('auth/login.html', login_text=login_text, password_text=password_text, all_messages=all_messages)

        valid, result, role = check_login(login_text, password_text)

        if not valid:
            # Increment failed attempts
            if user:
                user.failedAttempts += 1
                if user.failedAttempts >= 3:
                    user.isLocked = True
                    db.session.commit()
                    # Send reset password email
                    check_forgotPasswordEmail(user.userEmail)
                    flash("⚠️ Your account is locked. Please check your email for the reset password link.", "login_error")
                else:
                    db.session.commit()
                    flash(f"Invalid credentials. {3 - user.failedAttempts} attempts remaining.", "login_error")
            else:
                flash("No account found.", "login_error")

            all_messages = get_flashed_messages(with_categories=True)
            return render_template('auth/login.html', login_text=login_text, password_text=password_text, all_messages=all_messages)

        # Successful login — reset counters
        if user:
            user.failedAttempts = 0
            user.isLocked = False
            db.session.commit()

        session['user_id'] = result
        session['user_role'] = role

        if role == ADMIN:
            return redirect(url_for('admin_homepage'))
        elif role in (DEAN, HOS, HOP, LECTURER):
            return redirect(url_for('user_homepage'))
        else:
            flash("Unknown role", "login_error")
            return redirect(url_for('login'))

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
                userRegisterDateTime=datetime.now() + timedelta(hours=8)
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
# Main User Homepage
# -------------------------------
@app.route('/user/home', methods=['GET', 'POST'])
@login_required
def user_homepage():
    user_id = session.get('user_id')
    chosen = User.query.filter_by(userId=user_id).first()
    waiting = waiting_record(user_id)
    confirm = confirm_record(user_id).filter(Exam.examEndTime > (datetime.now() + timedelta(hours=8))).all()

    # Get open slots + gender filter
    open_slots = open_record(user_id)
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
                waiting_slot.timeAction = datetime.now() + timedelta(hours=8)

            elif action == 'reject':
                chosen.userPendingCumulativeHours = max((chosen.userPendingCumulativeHours or 0) - pending_hours, 0)
                waiting_slot.invigilationStatus = False

            waiting_slot.timeAction = datetime.now() + timedelta(hours=8)
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
            open_slot.timeAction = datetime.now() + timedelta(hours=8)

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
    """Return positive hour difference."""
    if not start or not end:
        return 0
    return max(0, (end.replace(tzinfo=None) - start.replace(tzinfo=None)).total_seconds() / 3600)

@app.template_filter('hours_format')
def hours_format(hours):
    h, m = divmod(round(hours * 60), 60)
    return f"{h}h {m}m" if h and m else (f"{h}h" if h else f"{m}m")

# -------------------------------
# Attendance route
# -------------------------------
@app.route('/attendance', methods=['POST'])
def attendance_record():
    try:
        data = request.get_json()
        card_input = data.get('cardNumber', '').strip()
        action_type = data.get('actionType', '').lower().strip()

        if not card_input:
            return jsonify({"success": False, "message": "Card scan missing!"})
        if action_type not in ['checkin', 'checkout']:
            return jsonify({"success": False, "message": "Invalid action type!"})

        # --- Use server Malaysia time only ---
        scan_time = datetime.now()

        # --- Get User ---
        user = User.query.filter_by(userCardId=card_input).first()
        if not user:
            return jsonify({"success": False, "message": "Card not recognized!"})

        # --- All exam attendance slots for user ---
        timeSlots = InvigilatorAttendance.query.filter_by(invigilatorId=user.userId).all()
        if not timeSlots:
            return jsonify({"success": False, "message": "No exam assigned!"})

        # --- Get all valid exam slots with exam info ---
        valid_slots = [att for att in timeSlots if att.report and att.report.exam]

        if not valid_slots:
            return jsonify({"success": False, "message": "Exam details missing!"})

        # --- Pick the closest exam by absolute time difference ---
        def exam_diff(att):
            exam = att.report.exam
            return abs((exam.examStartTime - scan_time).total_seconds())

        confirm = sorted(valid_slots, key=exam_diff)[0]

        exam = confirm.report.exam
        start = exam.examStartTime
        end = exam.examEndTime

        one_hour_before_start = start - timedelta(hours=1)
        last_valid_checkin = end - timedelta(minutes=30)
        checkout_expire = end + timedelta(hours=1)

        # --------------------------------
        # CHECK IN VALIDATION
        # --------------------------------
        if action_type == 'checkin':

            # Already checked in?
            if confirm.checkIn and not confirm.checkOut:
                return jsonify({"success": False, "message": "Already checked in!"})

            # Too early
            if scan_time < one_hour_before_start:
                return jsonify({"success": False, "message": "Too early to check in!"})

            # Too late
            if scan_time > last_valid_checkin:
                return jsonify({"success": False, "message": "Check-in is closed!"})

            # Assign check-in
            if scan_time <= start:
                remark = "CHECK IN"
            else:
                remark = "CHECK IN LATE"

            confirm.checkIn = scan_time
            confirm.remark = remark

        # --------------------------------
        # CHECK OUT VALIDATION
        # --------------------------------
        elif action_type == 'checkout':

            if not confirm.checkIn:
                return jsonify({"success": False, "message": "Please check in before checking out!"})

            if confirm.checkOut:
                return jsonify({"success": False, "message": "Already checked out!"})

            # Too late (after grace period)
            if scan_time > checkout_expire:
                confirm.checkOut = checkout_expire
                confirm.remark = "EXPIRED"

            # Early checkout (before exam end)
            elif scan_time < end:
                confirm.checkOut = scan_time
                confirm.remark = "CHECK OUT EARLY"

            # Normal checkout (during end → grace period)
            else:
                confirm.checkOut = scan_time
                if confirm.remark != "CHECK IN LATE":
                    confirm.remark = "COMPLETED"

        # --------------------------------
        # HOURS CALCULATION
        # --------------------------------
        if confirm.checkIn and confirm.checkOut:

            effective_start = max(confirm.checkIn, start)
            effective_end = min(confirm.checkOut, end)

            actual_hours = hours_diff(effective_start, effective_end)
            total_exam_hours = hours_diff(start, end)

            user.userCumulativeHours += actual_hours
            user.userPendingCumulativeHours -= total_exam_hours
            confirm.invigilationStatus = True

        db.session.commit()

        # Prepare response
        course = exam.course
        venues = [v.venueNumber for v in exam.venue_availabilities] if exam.venue_availabilities else []

        return jsonify({
            "success": True,
            "data": {
                "courseName": getattr(course, "courseName", "N/A"),
                "courseCode": getattr(course, "courseCodeSectionIntake", "N/A"),
                "students": getattr(course, "courseStudent", "N/A"),
                "examStart": start.strftime("%d/%b/%Y %H:%M"),
                "examEnd": end.strftime("%d/%b/%Y %H:%M"),
                "examVenue": ", ".join(venues) if venues else "N/A",
                "checkIn": confirm.checkIn.strftime("%d/%b/%Y %H:%M:%S") if confirm.checkIn else "None",
                "checkOut": confirm.checkOut.strftime("%d/%b/%Y %H:%M:%S") if confirm.checkOut else "None",
                "remark": confirm.remark or "",
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})


# -------------------------------
# RFID bridge routes
# -------------------------------
def reset_last_scan(delay=5):
    global last_scan_data
    time.sleep(delay)
    last_scan_data = {"cardNumber": None, "time": None}

@app.route('/update-last-scan', methods=['POST'])
def update_last_scan():
    global last_scan_data
    data = request.get_json()
    last_scan_data = {"cardNumber": data.get("cardNumber"), "time": data.get("time")}
    threading.Thread(target=reset_last_scan, args=(5,), daemon=True).start()  # ✅ auto clear
    return jsonify(success=True)

@app.route('/last-scan')
def get_last_scan():
    global last_scan_data
    return jsonify(last_scan_data)





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
    time_now = datetime.now()

    for attendance in all_attendance:
        report = attendance.report
        exam = report.exam if report else None
        if not exam or not exam.examEndTime or not exam.examStartTime:
            continue

        exam_duration = (exam.examEndTime - exam.examStartTime).total_seconds() / 3600.0

        # Case 1: Exam has ended, remark still PENDING (no check-in)
        if attendance.remark == "PENDING" and exam.examStatus == False:
            attendance.remark = "EXPIRED"
            if attendance.invigilator:
                # Remove pending hours
                attendance.invigilator.userPendingCumulativeHours -= exam_duration
                if attendance.invigilator.userPendingCumulativeHours < 0:
                    attendance.invigilator.userPendingCumulativeHours = 0

        # Case 2: Checked in (normal or late) but exam expired
        elif attendance.remark in ["CHECK IN", "CHECK IN LATE"] and time_now > (exam.examEndTime + timedelta(hours=1)):
            attendance.remark = "EXPIRED"
            if attendance.invigilator:
                if attendance.remark == "CHECK IN LATE" and attendance.checkIn:
                    # Actual worked hours: exam end - check-in late
                    worked_hours = (exam.examEndTime - attendance.checkIn).total_seconds() / 3600.0
                    if worked_hours < 0:
                        worked_hours = 0
                else:  # CHECK IN normal (no checkout)
                    worked_hours = exam_duration

                # Remove full exam duration from pending hours
                attendance.invigilator.userPendingCumulativeHours -= exam_duration
                if attendance.invigilator.userPendingCumulativeHours < 0:
                    attendance.invigilator.userPendingCumulativeHours = 0

                # Add worked hours to cumulative hours
                attendance.invigilator.userCumulativeHours += worked_hours

    db.session.commit()


def update_exam_status():
    # Auto-expire exams
    now = datetime.now() + timedelta(hours=8)
    expired_exams = Exam.query.filter(Exam.examEndTime < now, Exam.examStatus == True).all()
    for exam in expired_exams:
        exam.examStatus = False
    db.session.commit()







