# -------------------------------
# Third-party imports
# -------------------------------
from flask import render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from collections import defaultdict

# -------------------------------
# Local application imports
# -------------------------------
from app import app
from .authRoutes import login_required
from .backend import *
from .database import * 

# -------------------------------
# Flask and application setup
# -------------------------------
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()






# -------------------------------
# Calculate Invigilation Stats (Filtered by User Department or Own Data)
# -------------------------------
# -------------------------------
# Calculate Invigilation Stats (Filtered by User Department or Own Data)
# -------------------------------
def calculate_invigilation_stats():
    user = User.query.get(session.get('user_id'))

    # Base query: attendance joined with report, exam, and course
    base_query = (
        db.session.query(
            InvigilatorAttendance.attendanceId,
            InvigilatorAttendance.invigilatorId,
            InvigilatorAttendance.checkIn,
            InvigilatorAttendance.checkOut,
            Exam.examStartTime,
            Exam.examEndTime,
            InvigilatorAttendance.reportId
        )
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(Course, Course.courseExamId == Exam.examId)
    )

    # Apply role-based visibility filters
    if user.userLevel == 1:
        # Level 1 → Only own invigilation records
        filtered_query = base_query.filter(InvigilatorAttendance.invigilatorId == user.userId)
    else:
        # Level 2–4 → All records from the same department
        filtered_query = base_query.filter(Course.courseDepartment == user.userDepartment)

    # Calculate report totals before filtering to specific statuses
    total_report = filtered_query.count()
    total_active_report = filtered_query.filter(Exam.examStatus == True).count()

    # Retrieve only active invigilations for detailed time analysis
    records = (
        filtered_query
        .filter(Exam.examStatus == True)
        .filter(InvigilatorAttendance.invigilationStatus == True)
        .all()
    )

    # Initialize statistics
    stats = {
        "total_report": total_report,
        "total_activeReport": total_active_report,
        "total_checkInLate": 0,
        "total_checkOutEarly": 0,
    }

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
        .join(Course, Course.courseExamId == Exam.examId)  # ✅ join Course
        .join(User, InvigilatorAttendance.invigilatorId == User.userId)  # lecturer info
    )

    # Lecturer (Level 1) — see own only
    # .filter(InvigilatorAttendance.invigilationStatus == True)
    if user.userLevel == 1:
        query = query.filter(InvigilatorAttendance.invigilatorId == user.userId)

    # Dean, HOS, HOP (Level 2, 3, 4) — see all invigilations for courses under same department
    elif user.userLevel in [2, 3, 4]:
        query = query.filter(Course.courseDepartment == user.userDepartment)

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
        att.group_key = (not att.report.exam.examStatus, att.report.exam.examStartTime)
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

        def exam_dict(start, end):
            return {
                "exam_id": exam.examId,
                "course_name": exam.course.courseName,
                "course_code": exam.course.courseCodeSectionIntake,
                "venue": exam.examVenue,
                "start_time": start,
                "end_time": end,
                "status": exam.examStatus,
                "is_overnight": start_date != end_date
            }

        if start_date != end_date:
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


@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    userId = session.get('user_id')
    user = User.query.filter_by(userId=userId).first()
    
    # Pre-fill existing data
    userContact_text = ''
    userPassword1_text = ''
    userPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        userContact_text = request.form.get('contact', '').strip()
        userPassword1_text = request.form.get('password1', '').strip()
        userPassword2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(userId, userContact_text, userPassword1_text, userPassword2_text)
        if not valid:
            flash(message, 'error')
            return redirect(url_for('user_profile'))

        if valid and user:
            if userContact_text:
                user.userContact = userContact_text
            if userPassword1_text:
                hashed_pw = bcrypt.generate_password_hash(userPassword1_text).decode('utf-8')
                user.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('user_profile'))

    return render_template('user/userProfile.html', active_tab='user_profiletab', user=user, userContact_text=user.userContact if user else '',
                            userPassword1_text=userPassword1_text, userPassword2_text=userPassword2_text, error_message=error_message)



