
from flask import render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from collections import defaultdict
from app import app
from .authRoutes import login_required
from .backend import *
from .database import * 

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()




# -------------------------------
# Calculate Invigilation Stats (Filtered by User Department or Own Data)
# -------------------------------
def calculate_invigilation_stats():
    user = User.query.get(session.get('user_id'))

    # Base query for reports
    base_query = (
        db.session.query(InvigilationReport)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
    )

    # Role-based filters
    if user.userLevel == 1:
        # Level 1 → only reports the invigilator is assigned to
        filtered_query = (
            base_query.join(InvigilatorAttendance, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
            .filter(InvigilatorAttendance.invigilatorId == user.userId)
            .distinct()
        )
    else:
        # Level 2–4 → reports within same department
        filtered_query = base_query.filter(Course.courseDepartment == user.userDepartment).distinct()

    # Calculate report totals
    total_report = filtered_query.count()
    total_active_report = filtered_query.filter(Exam.examStatus == True).count()

    # Retrieve attendance data for detailed time analysis
    attendance_query = (
        db.session.query(
            InvigilatorAttendance.attendanceId,
            InvigilatorAttendance.invigilatorId,
            InvigilatorAttendance.checkIn,
            InvigilatorAttendance.checkOut,
            Exam.examStartTime,
            Exam.examEndTime,
            InvigilatorAttendance.reportId,
        )
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
        .filter(Exam.examStatus == True)
        .filter(InvigilatorAttendance.invigilationStatus == True)
    )

    # Apply the same visibility filter for attendance records
    if user.userLevel == 1:
        attendance_query = attendance_query.filter(InvigilatorAttendance.invigilatorId == user.userId)
    else:
        attendance_query = attendance_query.filter(Course.courseDepartment == user.userDepartment)

    records = attendance_query.all()

    # Initialize statistics
    stats = {
        "total_report": total_report,
        "total_activeReport": total_active_report,
        "total_checkInLate": 0,
        "total_checkOutEarly": 0,
    }

    # Analyze lateness / early checkout
    for row in records:
        if row.checkIn and row.checkIn > row.examStartTime:
            stats["total_checkInLate"] += 1
        if row.checkOut and row.checkOut < row.examEndTime:
            stats["total_checkOutEarly"] += 1

    return stats


def get_all_attendances():
    user = User.query.get(session.get('user_id'))
    query = (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)  # ✅ Join Course
        .join(User, InvigilatorAttendance.invigilatorId == User.userId)  # Lecturer info
    )

    # Lecturer (Level 1) — can see only their own invigilation records
    if user.userLevel == 1:
        query = query.filter(
            InvigilatorAttendance.invigilatorId == user.userId,
            InvigilatorAttendance.invigilationStatus == True
        )

    # Dean, HOS, HOP (Level 2, 3, 4) — can see all invigilations under same department
    elif user.userLevel in [2, 3, 4]:
        query = query.filter(Course.courseDepartment == user.userDepartment)

    # Order by exam status first (active > done), then by exam start time descending
    return query.order_by(Exam.examStatus.desc(), Exam.examStartTime.desc()).all()


# Lecturer get own
# DEAN, HOS, HOP get under own
@app.route('/user/invigilationReport', methods=['GET', 'POST'])
@login_required
def user_invigilationReport():
    attendances = get_all_attendances()
    stats = calculate_invigilation_stats()

    # Add composite group key: (examStatus, examStartTime)
    for att in attendances:
        report = att.report
        exam = Exam.query.get(report.examId) if report else None
        att.group_key = (
            not exam.examStatus if exam else True,
            exam.examStartTime if exam else datetime.min,
            exam.examId if exam else 0
        )
    return render_template('user/userInvigilationReport.html', active_tab='user_invigilationReporttab', attendances=attendances, **stats)
# -------------------------------
# Function for InviglationTimetable Route to read all the timetable in calendar mode
# -------------------------------
def get_calendar_data():
    attendances = get_all_attendances()
    calendar_data = defaultdict(list)
    seen_exams = set()  # ✅ To skip duplicate exam sessions

    for att in attendances:
        exam = att.report.exam

        # Skip if this exam already processed
        if exam.examId in seen_exams:
            continue
        seen_exams.add(exam.examId)

        start_dt = exam.examStartTime
        end_dt = exam.examEndTime
        start_date = start_dt.date()
        end_date = end_dt.date()
        is_overnight = start_date != end_date and exam.examStatus == True
        venues = exam.venue_availabilities

        def exam_dict(start, end):
            return {
                "exam_id": exam.examId,
                "course_name": exam.course.courseName,
                "course_code": exam.course.courseCodeSectionIntake.split('/')[0],
                "start_time": start,
                "end_time": end,
                "status": exam.examStatus,
                "is_overnight": is_overnight,
                "venue": [{"venueNumber": v.venueNumber, "capacity": v.capacity} for v in venues],
            }

        if is_overnight:
            # Part 1: From start time to 23:59 on start day
            calendar_data[start_date].append(
                exam_dict(start_dt, datetime.combine(start_date, datetime.max.time()).replace(hour=23, minute=59))
            )
            # Part 2: From 00:00 on next day to end time
            calendar_data[end_date].append(
                exam_dict(datetime.combine(end_date, datetime.min.time()), end_dt)
            )
        else:
            # Normal same-day exam
            calendar_data[start_date].append(exam_dict(start_dt, end_dt))

    calendar_data = dict(sorted(calendar_data.items()))
    return calendar_data

# -------------------------------
# Function for InviglationTimetable Route
# -------------------------------
@app.route('/user/invigilationTimetable', methods=['GET', 'POST'])
@login_required
def user_invigilationTimetable():
    calendar_data = get_calendar_data()
    return render_template('user/userInvigilationTimetable.html', active_tab='user_invigilationTimetabletab', calendar_data=calendar_data)



# -------------------------------
# Function for ViewOwnTimetable Route
# -------------------------------
@app.route('/user/ownTimetable', methods=['GET'])
@login_required
def user_ownTimetable():
    userId = session.get('user_id')
    user = User.query.filter_by(userId=userId).first()
    user_name = user.userName if user else "Unknown User"
    timetable = Timetable.query.filter_by(user_id=userId).first()
    timetable_rows = timetable.rows if timetable else []

    # Combine overlapping (same day & same time) entries
    merged = {}
    for row in timetable_rows:
        key = (row.classDay.upper(), row.classTime, row.classType, row.classRoom)
        if key not in merged:
            merged[key] = {
                'classDay': row.classDay,
                'classTime': row.classTime,
                'classType': row.classType,
                'classRoom': row.classRoom,
                'courseName': row.courseName,
                'courseIntakes': [row.courseIntake],
                'courseCodes': [row.courseCode],
                'courseSections': [row.courseSection]
            }
        else:
            merged[key]['courseIntakes'].append(row.courseIntake)
            merged[key]['courseCodes'].append(row.courseCode)
            merged[key]['courseSections'].append(row.courseSection)

    merged_timetable = []
    for item in merged.values():
        # zip the lists directly (combine element by element)
        item['combined'] = list(zip(item['courseIntakes'], item['courseCodes'], item['courseSections']))
        merged_timetable.append(item)

    return render_template('user/userOwnTimetable.html', active_tab='user_ownTimetabletab', timetable_rows=merged_timetable, user_name=user_name)


# -------------------------------
# Function for MergeTimetable Route
# -------------------------------
@app.route('/user/mergeTimetable', methods=['GET'])
@login_required
def user_mergeTimetable():
    userId = session.get('user_id')

    # Get the logged-in user's department
    current_user = User.query.filter_by(userId=userId).first()
    if not current_user:
        return redirect(url_for('user_mergeTimetable'))

    user_department = current_user.userDepartment
    selected_lecturer = request.args.get("lecturer")

    # Query all timetables for users in the same department
    timetables = (
        Timetable.query
        .join(User, Timetable.user_id == User.userId)
        .filter(User.userDepartment == user_department, User.userStatus == 1)
        .all()
    )

    # Collect all timetable rows
    timetable_rows = []
    for timetable in timetables:
        timetable_rows.extend(timetable.rows)

    # Filter by lecturer if selected
    if selected_lecturer:
        timetable_rows = [row for row in timetable_rows if row.lecturerName == selected_lecturer]

    # Extract unique lecturers for dropdown
    lecturers = sorted({row.lecturerName for row in timetable_rows})

    # Combine overlapping (same day & same time) entries
    merged = {}
    for row in timetable_rows:
        key = (row.classDay.upper(), row.classTime, row.classType, row.classRoom)
        if key not in merged:
            merged[key] = {
                'classDay': row.classDay,
                'classTime': row.classTime,
                'classType': row.classType,
                'classRoom': row.classRoom,
                'courseName': row.courseName,
                'lecturerName': row.lecturerName,
                'courseIntakes': [row.courseIntake],
                'courseCodes': [row.courseCode],
                'courseSections': [row.courseSection]
            }
        else:
            merged[key]['courseIntakes'].append(row.courseIntake)   
            merged[key]['courseCodes'].append(row.courseCode)
            merged[key]['courseSections'].append(row.courseSection)

    # Build merged timetable list for rendering
    merged_timetable = []
    for item in merged.values():
        item['combined'] = list(zip(item['courseIntakes'], item['courseCodes'], item['courseSections']))
        merged_timetable.append(item)

    return render_template('user/userMergeTimetable.html', active_tab='user_mergeTimetabletab', timetable_rows=merged_timetable, user_department=user_department, lecturers=lecturers, selected_lecturer=selected_lecturer)



@app.route('/user/viewStaff', methods=['GET'])
@login_required
def user_viewStaff():
    userId = session.get('user_id')
    current_user = User.query.filter_by(userId=userId).first()
    if not current_user:
        flash("User not found.", "danger")
        return redirect(url_for('user_dashboard'))

    # Get all staff from the same department
    lecturers = User.query.filter_by(userDepartment=current_user.userDepartment)
    # Counts filtered by department
    total_admin = lecturers.filter_by(userLevel=5).count()
    total_hop = lecturers.filter_by(userLevel=4).count()
    total_hos = lecturers.filter_by(userLevel=3).count()
    total_dean = lecturers.filter_by(userLevel=2).count()
    total_lecturer = lecturers.filter_by(userLevel=1).count()
    total_male_staff = lecturers.filter_by(userGender="MALE").count()
    total_female_staff = lecturers.filter_by(userGender="FEMALE").count()
    total_activated = lecturers.filter_by(userStatus=1).count()
    total_deactivate = lecturers.filter_by(userStatus=0).count()
    total_deleted = lecturers.filter_by(userStatus=2).count()

    # Department filter
    dept_filter = User.userDepartment == current_user.userDepartment
    # Incomplete rows check within the same department
    error_rows = User.query.filter(
        dept_filter,
        (
            (User.userDepartment.is_(None)) | (User.userDepartment == '') |
            (User.userName.is_(None)) | (User.userName == '') |
            (User.userEmail.is_(None)) | (User.userEmail == '') |
            (User.userContact.is_(None)) | (User.userContact == '') |
            (User.userGender.is_(None)) | (User.userGender == '') |
            (User.userLevel.is_(None))
        )
    ).count()

    return render_template('user/userViewStaff.html', active_tab='user_viewStafftab',lecturers=lecturers,total_admin=total_admin,total_hop=total_hop,total_hos=total_hos,total_dean=total_dean,error_rows=error_rows,
                           total_lecturer=total_lecturer,total_male_staff=total_male_staff,total_female_staff=total_female_staff,total_activated=total_activated,total_deactivate=total_deactivate,total_deleted=total_deleted)

# -------------------------------
# Function for Profile Route
# -------------------------------
@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    userId = session.get('user_id')
    user = User.query.filter_by(userId=userId).first()
    
    # Pre-fill existing data
    userCardUID = user.userCardId or ''
    userContact_text = user.userContact or ''
    userPassword1_text = ''
    userPassword2_text = ''

    if request.method == 'POST':
        userCardUID = request.form.get('cardUID', '').strip().replace(' ', '')
        userContact_text = request.form.get('contact', '').strip()
        userPassword1_text = request.form.get('password1', '').strip()
        userPassword2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(userId, userCardUID, userContact_text, userPassword1_text, userPassword2_text)
        if not valid:
            flash(message, 'error')
            return redirect(url_for('user_profile'))

        if valid and user:
            user.userContact = userContact_text or None
            user.userCardId = userCardUID or None
            # Update password only if entered
            if userPassword1_text:
                hashed_pw = bcrypt.generate_password_hash(userPassword1_text).decode('utf-8')
                user.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('user_profile'))

    return render_template('user/userProfile.html', active_tab='user_profiletab', user=user, userContact_text=user.userContact if user else '',
                            userPassword1_text=userPassword1_text, userPassword2_text=userPassword2_text, error_message=error_message)



