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
            # record_action("LOGIN", "LOGIN", user.userId, user.userId)
            user.failedAttempts = 0
            user.isLocked = False
            db.session.commit()

        session['user_id'] = result
        session['user_role'] = role

        if role == "ADMIN":
            return redirect(url_for('admin_homepage'))
        elif role in ("DEAN", "HOS", "HOP", "LECTURER", "PROGRAM OFFICERS"):
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
    department_data = Department.query.all()
    id_text = ''
    card_text = ''
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
        card_text = request.form.get('cardid', '').strip()
        name_text = request.form.get('username', '').strip()
        email_text = request.form.get('email', '').strip()
        contact_text = request.form.get('contact', '').strip()
        department_text = request.form.get('department', '').strip()
        role_text = request.form.get('role', '').strip()
        gender_text = request.form.get('gender', '').strip()
        password1_text = request.form.get('password1', '').strip()
        password2_text = request.form.get('password2', '').strip()

        is_valid, error_message = check_register(id_text, card_text, email_text, contact_text, password1_text, password2_text)
        # Convert to boolean
        # Assuming 0 = Female (False), 1 = Male (True)
        gender_bool = True if gender_text == "1" else False

        if error_message:
            flash(error_message, 'error')
        elif is_valid:
            hashed_pw = bcrypt.generate_password_hash(password1_text).decode('utf-8')
            new_user = User(
                userId=id_text,
                userName=name_text.upper(),
                userDepartment=department_text.upper(),
                userEmail=email_text,
                userContact=contact_text,
                userPassword=hashed_pw,
                userGender=gender_bool,
                userStatus=0,  # not verified yet
                userCardId=card_text,
                userLevel=role_text
            )
            db.session.add(new_user)
            # record_action("REGISTER AS NEW USER", "REGISTER", id_text, id_text)
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
    confirm = confirm_record(user_id)
    reject = reject_record(user_id)

    # Get open slots + gender filter
    open_slots = open_record(user_id)
    if chosen:
        open_slots = [slot for slot in open_slots if slot.invigilator.userGender == chosen.userGender]

    if request.method == 'POST':
        action = request.form.get('action')

        # -----------------------------
        # Handle waiting approval/rejection
        # -----------------------------
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

            course_code = exam.course.courseCodeSectionIntake if exam and exam.course else "Unknown"
            pending_hours = 0
            if exam and exam.examStartTime and exam.examEndTime:
                start_dt, end_dt = exam.examStartTime, exam.examEndTime
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                pending_hours = (end_dt - start_dt).total_seconds() / 3600.0

            if action == 'accept':
                waiting_slot.invigilationStatus = True
                waiting_slot.timeAction = datetime.now() + timedelta(hours=8)
                db.session.commit()
                flash(f"{course_code} have been accepted", "success")
                return redirect(url_for('user_homepage'))

            elif action == 'reject':
                # Process reject reason
                raw_reason = request.form.get('reject_reason', '')
                lines = [line.strip() for line in raw_reason.splitlines() if line.strip()]
                waiting_slot.rejectReason = ','.join(lines)

                # ✅ Subtract hours for the user
                chosen.userPendingCumulativeHours = max((chosen.userPendingCumulativeHours or 0) - pending_hours, 0)

                waiting_slot.invigilationStatus = False

                # Create new record for reassignment (unassigned slot)
                db.session.add(
                    InvigilatorAttendance(
                        reportId=waiting_slot.reportId,
                        invigilatorId=waiting_slot.invigilatorId,
                        venueNumber=waiting_slot.venueNumber,
                        timeExpire=waiting_slot.timeExpire,
                        timeCreate=datetime.now(timezone.utc) + timedelta(hours=8)
                    )
                )

                waiting_slot.timeAction = datetime.now() + timedelta(hours=8)
                db.session.commit()
                flash(f"{course_code} has been rejected", "success")
                return redirect(url_for('user_homepage'))

        # -----------------------------
        # Handle open slot acceptance
        # -----------------------------
        open_attendance_id = request.form.get('a_id')
        if action == 'open_accept' and chosen:

            # Step 0: Fetch the slot by attendanceId from the form
            form_slot = InvigilatorAttendance.query.filter_by(attendanceId=open_attendance_id).first()
            if not form_slot:
                flash("Selected slot not found.", "error")
                return redirect(url_for('user_homepage'))

            report_id = form_slot.reportId

            # Step 1: Try to fetch user's own unaccepted slot for this report
            open_slot = (
                InvigilatorAttendance.query
                .filter(
                    InvigilatorAttendance.reportId == report_id,
                    InvigilatorAttendance.invigilatorId == user_id,
                    InvigilatorAttendance.invigilationStatus == False
                )
                .order_by(InvigilatorAttendance.attendanceId.desc())
                .first()
            )

            # Step 2: Fallback to the slot from the form if no own slot exists
            if not open_slot:
                open_slot = form_slot

            # Step 3: Get exam and course info
            exam = (
                Exam.query
                .join(InvigilationReport, Exam.examId == InvigilationReport.examId)
                .filter(InvigilationReport.invigilationReportId == open_slot.reportId)
                .first()
            )
            course_code = exam.course.courseCodeSectionIntake if exam and exam.course else "Unknown"

            # Step 4: Gender check
            if open_slot.invigilator and open_slot.invigilator.userGender != chosen.userGender:
                flash("Cannot accept: slot reserved for same-gender invigilators only.", "error")
                return redirect(url_for('user_homepage'))

            # Step 5: Check for time conflicts with already assigned slots
            def is_overlap(start1, end1, start2, end2):
                return max(start1, start2) < min(end1, end2)

            # Candidate exam times
            candidate_start, candidate_end = exam.examStartTime, exam.examEndTime
            if candidate_end < candidate_start:
                candidate_end += timedelta(days=1)

            # Fetch all accepted slots for the user
            existing_slots = (
                InvigilatorAttendance.query
                .join(InvigilationReport, InvigilationReport.invigilationReportId == InvigilatorAttendance.reportId)
                .join(Exam, Exam.examId == InvigilationReport.examId)
                .filter(
                    InvigilatorAttendance.invigilatorId == user_id,
                    InvigilatorAttendance.invigilationStatus == True
                )
                .all()
            )

            # Check for overlap
            conflict = False
            for slot in existing_slots:
                s_exam = slot.report.exam
                start_dt, end_dt = s_exam.examStartTime, s_exam.examEndTime
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                if is_overlap(start_dt, end_dt, candidate_start, candidate_end):
                    conflict = True
                    break

            if conflict:
                flash("Cannot accept this slot: timing overlaps with another assigned exam.", "error")
                return redirect(url_for('user_homepage'))

            # Step 6: Subtract pending hours from previous invigilator if slot reassigned
            if open_slot.invigilatorId and open_slot.invigilatorId != user_id:
                prev_user = User.query.get(open_slot.invigilatorId)
                if prev_user and exam:
                    hours_to_remove = (candidate_end - candidate_start).total_seconds() / 3600.0
                    prev_user.userPendingCumulativeHours = max((prev_user.userPendingCumulativeHours or 0) - hours_to_remove, 0)

            # Step 7: Assign slot to current user
            open_slot.invigilatorId = user_id
            open_slot.invigilationStatus = True
            open_slot.rejectReason = None  # clear previous reject reason
            open_slot.timeAction = datetime.now() + timedelta(hours=8)

            # Step 8: Add pending hours to current user
            hours_to_add = (candidate_end - candidate_start).total_seconds() / 3600.0

            # Avoid double-counting: check if the user already has a waiting slot for this exam
            existing_waiting = (
                InvigilatorAttendance.query
                .join(InvigilationReport, InvigilationReport.invigilationReportId == InvigilatorAttendance.reportId)
                .filter(
                    InvigilatorAttendance.invigilatorId == user_id,
                    InvigilatorAttendance.invigilationStatus == False,
                    InvigilatorAttendance.timeAction.is_(None),
                    InvigilationReport.examId == exam.examId
                )
                .first()
            )
            if not existing_waiting:
                chosen.userPendingCumulativeHours = (chosen.userPendingCumulativeHours or 0) + hours_to_add
            
            db.session.commit()
            flash(f"Open Slot Course Code: {course_code} Accepted Successfully", "success")
            return redirect(url_for('user_homepage'))
    return render_template('user/userHomepage.html', active_tab='user_hometab', waiting=waiting, confirm=confirm, open=open_slots, reject=reject)



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
last_scan_data = {"cardNumber": None, "time": None}
@app.route('/attendance', methods=['GET', 'POST'])
def attendance_record():
    global last_scan_data
    if request.method == 'POST':
        try:
            data = request.get_json()
            last_scan_data = {"cardNumber": data.get('cardNumber'), "time": datetime.now().isoformat()}
            card_input = data.get('cardNumber', '').replace(' ', '')
            action_type = data.get('actionType', '').lower().strip()
            click_time_str = data.get('clickTime', None)

            if not card_input:
                return jsonify({"success": False, "message": "Card scan missing!"})
            if action_type not in ['checkin', 'checkout']:
                return jsonify({"success": False, "message": "Invalid action type!"})

            # Find user by card
            user = User.query.filter_by(userCardId=card_input).first()
            if not user:
                return jsonify({"success": False, "message": "Card not recognized!"})
            user_id = user.userId

            # Fetch attendance records for this invigilator
            timeSlots = InvigilatorAttendance.query.filter_by(invigilatorId=user_id).all()
            if not timeSlots:
                return jsonify({"success": False, "message": "No exam assigned!"})

            # Malaysia local time (UTC +8)
            scan_time = datetime.utcnow() 

            # Optional: use click time from browser if provided
            if click_time_str:
                try:
                    click_time = datetime.fromisoformat(click_time_str.replace("Z", "+00:00")) + timedelta(hours=8)
                    scan_time = click_time.replace(tzinfo=None)
                except Exception:
                    pass
            else:
                scan_time = scan_time.replace(tzinfo=None)

            # Helper: find the exam nearest to scan_time
            def exam_proximity(att):
                exam = getattr(att.report, "exam", None)
                if not exam or not exam.examStartTime:
                    return float("inf")
                exam_start = exam.examStartTime.replace(tzinfo=None)
                return abs((exam_start - scan_time).total_seconds())

            # Instead of picking the closest exam blindly
            valid_slots = [att for att in timeSlots if att.report and att.report.exam]
            upcoming_slots = [att for att in valid_slots
                            if att.report.exam.examStartTime.replace(tzinfo=None) - timedelta(hours=1) <= scan_time <=
                                att.report.exam.examEndTime.replace(tzinfo=None) + timedelta(hours=1)]

            if not upcoming_slots:
                return jsonify({"success": False, "message": "No upcoming exam slot within 1 hour!"})

            confirm = sorted(upcoming_slots, key=exam_proximity)[0]
            report = getattr(confirm, "report", None)
            exam = getattr(report, "exam", None)
            if not exam or not exam.examStartTime or not exam.examEndTime:
                return jsonify({"success": False, "message": "Exam details missing!"})

            # Convert to naive Malaysia time
            start = exam.examStartTime.replace(tzinfo=None)
            end = exam.examEndTime.replace(tzinfo=None)
            one_hour_before = start - timedelta(hours=1)

            # Only valid if scan is within 1 hour before start
            if scan_time < one_hour_before:
                return jsonify({"success": False, "message": "No upcoming exam slot within 1 hour!"})

            # CHECK-IN LOGIC
            if action_type == 'checkin':
                # Check if exam already ended
                if scan_time > end:
                    return jsonify({"success": False, "message": "Exam already ended!"})

                # Check if already checked in within this exam period
                if confirm.checkIn and confirm.checkOut is None and start <= scan_time <= end:
                    return jsonify({"success": False, "message": "Already checked in!"})

                # Check-in time rules
                if one_hour_before <= scan_time <= start:
                    confirm.checkIn = scan_time
                    confirm.remark = "CHECK IN"
                elif start < scan_time <= (end - timedelta(minutes=30)):
                    confirm.checkIn = scan_time
                    confirm.remark = "CHECK IN LATE"
                else:
                    return jsonify({"success": False, "message": "Not allowed to check in after 30 mins before exam end!"})

            # CHECK-OUT LOGIC
            elif action_type == 'checkout':
                if not confirm.checkIn:
                    return jsonify({"success": False, "message": "Please check in before checking out!"})
                if confirm.checkOut:
                    return jsonify({"success": False, "message": "Already checked out!"})

                expire_time = end + timedelta(hours=1)
                if scan_time < end:
                    # Checked out before exam end
                    confirm.checkOut = scan_time
                    confirm.remark = "CHECK OUT EARLY"
                elif end <= scan_time <= expire_time:
                    # Checked out normally (on time or slightly after)
                    if confirm.remark == "CHECK IN LATE":
                        # Keep previous remark if already late check-in
                        confirm.checkOut = scan_time
                        confirm.remark = "CHECK IN LATE"
                    else:
                        confirm.checkOut = scan_time
                        confirm.remark = "COMPLETED"
                else:
                    # Checked out too late (after grace period)
                    confirm.checkOut = expire_time
                    confirm.remark = "EXPIRED"

            # Hours & Status update
            if confirm.checkIn and confirm.checkOut:
                exam_hours = hours_diff(start, end)
                # Determine effective start
                effective_start = start if confirm.checkIn < start else confirm.checkIn
                # Determine effective end
                effective_end = end if confirm.checkOut > end else confirm.checkOut
                # Compute actual working hours
                actual_hours = hours_diff(effective_start, effective_end)
                # Adjust cumulative hours correctly
                user.userPendingCumulativeHours -= exam_hours
                user.userCumulativeHours += actual_hours
                confirm.invigilationStatus = True
            db.session.commit()

            # Prepare response
            course = getattr(exam, "course", None)
            venues = []
            if getattr(exam, "venue_availabilities", None):
                venues = [v.venueNumber for v in exam.venue_availabilities]
            venue_list = ", ".join(venues) if venues else "N/A"

            response_data = {
                "courseName": getattr(course, "courseName", "N/A"),
                "courseCode": getattr(course, "courseCodeSectionIntake", "N/A"),
                "students": getattr(course, "courseStudent", "N/A"),
                "examStart": start.strftime("%d/%b/%Y %H:%M"),
                "examEnd": end.strftime("%d/%b/%Y %H:%M"),
                "examVenue": venue_list,
                "checkIn": confirm.checkIn.strftime("%d/%b/%Y %H:%M:%S") if confirm.checkIn else "None",
                "checkOut": confirm.checkOut.strftime("%d/%b/%Y %H:%M:%S") if confirm.checkOut else "None",
                "remark": confirm.remark or "",
            }
            return jsonify({"success": True, "data": response_data})

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Attendance record failed: {e}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"})

    return render_template('auth/attendance.html')

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
            attendance.timeAction = time_now
            attendance.invigilationStatus = True
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






