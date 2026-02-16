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

        valid, result, role, department = check_login(login_text, password_text)

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
        session['user_department'] = department
        record_action(f"LOGIN AS [{department}-{role}]", "LOGIN", result, result)

        if role == "ADMIN":
            return redirect(url_for('admin_homepage'))
        elif role in ("DEAN", "HOS", "HOP", "LECTURER", "PO", "LAB_ASST"):
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
            record_action(f"REGISTER AS [{department_text.upper()}-{role_text}]", "REGISTER", id_text, id_text)
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
    user_id = session.get('user_id')
    role = session.get('user_role')
    department = session.get('user_department')
    if user_id and role:
        record_action(f"LOGOUT AS [{role}-{department}]", "LOGOUT", user_id, user_id)
    
    session.clear()
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









def get_available_positions(session_obj, exclude_slot_id=None):
    # Calculate total students
    total_students = sum(
        ve.exam.totalStudents or 0
        for ve in session_obj.exams
        if ve.exam
    )

    required_chief = 1
    required_inv = 1 if total_students <= 32 else 2

    query = VenueSessionInvigilator.query.filter(
        VenueSessionInvigilator.venueSessionId == session_obj.venueSessionId,
        VenueSessionInvigilator.invigilationStatus == True
    )

    # FIX: exclude by PRIMARY KEY (sessionId)
    if exclude_slot_id:
        query = query.filter(VenueSessionInvigilator.sessionId != exclude_slot_id)

    confirmed = query.all()
    chief_count = sum(1 for c in confirmed if c.position == "CHIEF")
    inv_count = sum(1 for c in confirmed if c.position == "INVIGILATOR")

    allowed = []
    if chief_count < required_chief:
        allowed.append("CHIEF")
    if inv_count < required_inv:
        allowed.append("INVIGILATOR")
    return allowed




# -------------------------------
# Main User Homepage
# -------------------------------
@app.route('/user/home', methods=['GET', 'POST'])
@login_required
def user_homepage():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    waiting = waiting_record(user_id)
    confirm = confirm_record(user_id)
    reject = reject_record(user_id)
    open_slots = open_record(user_id)

    backup = (
        VenueSessionInvigilator.query
        .join(VenueSession)
        .join(VenueExam)
        .join(Exam)
        .filter(
            VenueSession.backupInvigilatorId.is_(None),   # Backup not yet assigned
            Exam.examStatus == 1,                         # Only active exams
            (VenueSessionInvigilator.invigilatorId != user_id) | (VenueSessionInvigilator.invigilatorId.is_(None))  # Not assigned to current user
        )
        .group_by(VenueSession.venueNumber)
        .all()
    )

    confirm_with_roles = []
    for c in confirm:
        if c.session:
            c.allowed_roles = get_available_positions(
                c.session,
                exclude_slot_id=c.venueSessionId
            )
        else:
            c.allowed_roles = []
        confirm_with_roles.append(c)


    if request.method == 'POST':
        action = request.form.get('action')

        # -----------------------------
        # Handle waiting slot accept/reject
        # -----------------------------
        if action in ['accept', 'reject']:
            waiting_id = request.form.get('w_id')
            waiting_slot = VenueSessionInvigilator.query.filter_by(
                venueSessionId=waiting_id,
                invigilatorId=user_id
            ).first()

            if not waiting_slot or not waiting_slot.session:
                flash("Selected slot not found.", "error")
                return redirect(url_for('user_homepage'))

            session_obj = waiting_slot.session
            candidate_start, candidate_end = session_obj.startDateTime, session_obj.endDateTime
            hours = (candidate_end - candidate_start).total_seconds() / 3600.0

            if action == 'accept':
                waiting_slot.invigilationStatus = True
                waiting_slot.timeAction = datetime.now() + timedelta(hours=8)
                db.session.commit()
                flash(f"Slot at Venue: {session_obj.venue.venueNumber} accepted successfully.", "success")
                record_action("ACCEPT", "INVIGILATOR", session_obj.venue.venueNumber, user_id)
                return redirect(url_for('user_homepage'))

            elif action == 'reject':
                raw_reason = request.form.get('reject_reason', '')
                waiting_slot.remark = "REJECTED"
                waiting_slot.rejectReason = raw_reason.strip()
                waiting_slot.timeAction = datetime.now() + timedelta(hours=8)
                waiting_slot.invigilationStatus = False

                # Rollback pending hours
                if user:
                    user.userPendingCumulativeHours = max((user.userPendingCumulativeHours or 0) - hours, 0)

                # Optional: create a new unassigned slot for reassignment
                db.session.add(
                    VenueSessionInvigilator(
                        venueSessionId=waiting_slot.venueSessionId,
                        invigilatorId=None,
                        checkIn=None,
                        checkOut=None,
                        timeCreate=waiting_slot.timeCreate,
                        position=waiting_slot.position,
                        timeExpire=waiting_slot.timeExpire,
                        invigilationStatus=False,
                        remark="PENDING"
                    )
                )
                db.session.commit()
                flash(f"Slot at Venue: {session_obj.venue.venueNumber} rejected successfully.", "success")
                record_action("REJECT", "INVIGILATOR", session_obj.venue.venueNumber, user_id)
                return redirect(url_for('user_homepage'))

        # -----------------------------
        # Handle open slot acceptance
        # -----------------------------
        elif action == 'open_accept':
            open_attendance_id = request.form.get('open_id')

            slot = (
                db.session.query(VenueSessionInvigilator)
                .filter_by(sessionId=open_attendance_id)
                .with_for_update()  # ✅ Prevent double booking
                .first()
            )

            if not slot:
                flash("Slot not found.", "danger")
                return redirect(url_for('user_homepage'))

            session_obj = slot.session

            # Conflict check
            user_confirmed = VenueSessionInvigilator.query.filter(
                VenueSessionInvigilator.invigilatorId == user_id,
                VenueSessionInvigilator.invigilationStatus == True
            ).all()

            for c in user_confirmed:
                if c.venueSessionId == session_obj.venueSessionId:
                    flash("You are already assigned to this session.", "danger")
                    return redirect(url_for('user_homepage'))

                if c.session.startTime == session_obj.startTime:
                    flash("Time conflict detected.", "danger")
                    return redirect(url_for('user_homepage'))

            available_positions = get_available_positions(session_obj)

            if not available_positions:
                flash("No available roles left.", "danger")
                return redirect(url_for('user_homepage'))

            chosen_position = available_positions[0]

            slot.invigilatorId = user_id
            slot.position = chosen_position
            slot.invigilationStatus = True
            slot.remark = None
            db.session.commit()

            flash("Open slot accepted successfully!", "success")
            return redirect(url_for('user_homepage'))


        # -----------------------------
        # Handle backup slot assignment
        # -----------------------------
        elif action == 'backup':
            backup_attendance_id = request.form.get('b_id')
            slot = VenueSessionInvigilator.query.get(backup_attendance_id)
            if not slot or not slot.session:
                flash("Selected backup slot not found.", "error")
                return redirect(url_for('user_homepage'))

            session_obj = slot.session
            # Assign backup user to session
            session_obj.backupInvigilatorId = user_id

            # Check if this user already has a row for this session
            existing_slot = VenueSessionInvigilator.query.filter_by(
                venueSessionId=session_obj.venueSessionId,
                invigilatorId=user_id
            ).first()

            if existing_slot:
                # Just convert existing record into BACKUP
                existing_slot.position = 'BACKUP'
                existing_slot.invigilationStatus = False
                existing_slot.remark = "PENDING"
                existing_slot.timeAction = datetime.now() + timedelta(hours=8)
            else:
                # Create new record safely
                new_backup_slot = VenueSessionInvigilator(
                    venueSessionId=session_obj.venueSessionId,
                    invigilatorId=user_id,
                    checkIn=None,
                    checkOut=None,
                    timeCreate=datetime.now() + timedelta(hours=8),
                    position='BACKUP',
                    timeExpire=datetime.now() + timedelta(hours=8),
                    timeAction=datetime.now() + timedelta(hours=8),
                    invigilationStatus=False,
                    remark="PENDING"
                )
                db.session.add(new_backup_slot)
            db.session.commit()
            flash(f"You are now assigned as BACKUP for Venue: {session_obj.venue.venueNumber}.", "success")
            record_action("BACKUP", "INVIGILATOR", session_obj.venue.venueNumber, user_id)
            return redirect(url_for('user_homepage'))


        elif action == 'update_position':
            c_id = request.form.get('c_id')
            new_position = request.form.get('new_position')

            if not c_id or not new_position:
                flash("Invalid request.", "error")
                return redirect(url_for('user_homepage'))

            slot = (
                db.session.query(VenueSessionInvigilator)
                .filter_by(sessionId=c_id)
                .with_for_update()  # ✅ RACE SAFE
                .first()
            )

            if not slot:
                flash("Slot not found.", "danger")
                return redirect(url_for('user_homepage'))

            if slot.invigilatorId != user_id:
                flash("Unauthorized action.", "error")
                return redirect(url_for('user_homepage'))

            allowed = get_available_positions(
                slot.session,
                exclude_slot_id=slot.sessionId  # ✅ FIX
            )

            if new_position not in allowed:
                flash("Selected role is no longer available.", "danger")
                return redirect(url_for('user_homepage'))

            slot.position = new_position
            db.session.commit()
            flash("Position updated successfully.", "success")
            return redirect(url_for('user_homepage'))



    return render_template(
        'user/userHomepage.html',
        active_tab='user_hometab',
        waiting=waiting,
        confirm=confirm_with_roles,
        open=open_slots,
        reject=reject,
        backup=backup
    )



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
# Attendance route (for VenueSessionInvigilator)
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

            # --- Find user ---
            user = User.query.filter_by(userCardId=card_input).first()
            if not user:
                return jsonify({"success": False, "message": "Card not recognized!"})

            # --- Scan time in Malaysia UTC+8 ---
            scan_time = datetime.utcnow()
            if click_time_str:
                try:
                    scan_time = datetime.fromisoformat(click_time_str.replace("Z", "+00:00")) + timedelta(hours=8)
                    scan_time = scan_time.replace(tzinfo=None)
                except Exception:
                    pass
            else:
                scan_time = scan_time.replace(tzinfo=None)

            # --- Fetch all invigilator slots ---
            slots = VenueSessionInvigilator.query.filter_by(invigilatorId=user.userId).all()
            if not slots:
                return jsonify({"success": False, "message": "No assigned sessions!"})

            # --- Filter slots within 1 hour before/after session ---
            upcoming_slots = [
                s for s in slots
                if s.session and s.session.startDateTime - timedelta(hours=1) <= scan_time <= s.session.endDateTime + timedelta(hours=1)
            ]
            if not upcoming_slots:
                return jsonify({"success": False, "message": "No session within 1 hour!"})

            # --- Pick nearest session ---
            def slot_proximity(s):
                return abs((s.session.startDateTime.replace(tzinfo=None) - scan_time).total_seconds())
            slot = sorted(upcoming_slots, key=slot_proximity)[0]
            session_obj = slot.session
            course = getattr(session_obj, "course", None) or getattr(session_obj.exam, "course", None)

            start = session_obj.startDateTime.replace(tzinfo=None)
            end = session_obj.endDateTime.replace(tzinfo=None)
            one_hour_before = start - timedelta(hours=1)
            expire_time = end + timedelta(hours=1)

            # --- Check-in ---
            if action_type == 'checkin':
                if scan_time > end:
                    return jsonify({"success": False, "message": "Session already ended!"})
                if slot.checkIn and not slot.checkOut:
                    return jsonify({"success": False, "message": "Already checked in!"})

                if one_hour_before <= scan_time <= start:
                    slot.checkIn = scan_time
                    slot.remark = "CHECK IN"
                elif start < scan_time <= end - timedelta(minutes=30):
                    slot.checkIn = scan_time
                    slot.remark = "CHECK IN LATE"
                else:
                    return jsonify({"success": False, "message": "Cannot check in after 30 mins before session end!"})

            # --- Check-out ---
            elif action_type == 'checkout':
                if not slot.checkIn:
                    return jsonify({"success": False, "message": "Please check in before checking out!"})
                if slot.checkOut:
                    return jsonify({"success": False, "message": "Already checked out!"})

                if scan_time < end:
                    slot.checkOut = scan_time
                    slot.remark = "CHECK OUT EARLY"
                elif end <= scan_time <= expire_time:
                    slot.checkOut = scan_time
                    if slot.remark == "CHECK IN LATE":
                        slot.remark = "CHECK IN LATE"
                    else:
                        slot.remark = "COMPLETED"
                else:
                    slot.checkOut = expire_time
                    slot.remark = "EXPIRED"

            # --- Hours calculation ---
            if slot.checkIn and slot.checkOut:
                effective_start = max(slot.checkIn, start)
                effective_end = min(slot.checkOut, end)
                actual_hours = round((effective_end - effective_start).total_seconds() / 3600.0, 2)
                session_hours = round((end - start).total_seconds() / 3600.0, 2)
                user.userPendingCumulativeHours = max((user.userPendingCumulativeHours or 0) - session_hours, 0)
                user.userCumulativeHours = (user.userCumulativeHours or 0) + actual_hours
                slot.invigilationStatus = True

            db.session.commit()

            # --- Response ---
            venue_list = getattr(session_obj, "venue", None)
            venue_str = venue_list.venueNumber if venue_list else "N/A"

            return jsonify({
                "success": True,
                "data": {
                    "courseName": getattr(course, "courseName", "N/A"),
                    "courseCode": getattr(course, "courseCodeSectionIntake", "N/A"),
                    "examStart": start.strftime("%d/%b/%Y %H:%M"),
                    "examEnd": end.strftime("%d/%b/%Y %H:%M"),
                    "examVenue": venue_str,
                    "checkIn": slot.checkIn.strftime("%d/%b/%Y %H:%M:%S") if slot.checkIn else "None",
                    "checkOut": slot.checkOut.strftime("%d/%b/%Y %H:%M:%S") if slot.checkOut else "None",
                    "remark": slot.remark
                }
            })

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


def update_exam_status():
    now = datetime.now(timezone.utc)

    # Join Exam -> VenueExam -> VenueSession
    expired_exams = (
        db.session.query(Exam)
        .join(VenueExam)
        .join(VenueSession)
        .filter(VenueSession.endDateTime < now)
        .filter(Exam.examStatus == True)
        .all()
    )

    for exam in expired_exams:
        exam.examStatus = False

    db.session.commit()





'''
def update_attendanceStatus():
    all_attendance = InvigilatorAttendance.query.all()
    time_now = datetime.now()

    for attendance in all_attendance:
        report = attendance.report
        exam = report.exam if report else None
        # if not exam or not exam.examEndTime or not exam.examStartTime:
        #     continue

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
'''





