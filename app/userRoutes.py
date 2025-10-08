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
# Calculate All InvigilatorAttendance and InvigilationReport Data From Database
# -------------------------------
def calculate_invigilation_stats():
    query = (
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
        .filter(InvigilatorAttendance.invigilationStatus == True)
        .filter(Exam.examStatus == True)
        .all()
    )

    # Total reports and total assigned invigilators
    total_report = InvigilationReport.query.count()
    total_invigilator = InvigilatorAttendance.query.count()

    stats = {
        "total_report": total_report,
        "total_invigilator": total_invigilator,
        "total_checkInOnTime": 0,
        "total_checkInLate": 0,
        "total_checkOutOnTime": 0,
        "total_checkOutEarly": 0,
        "total_checkInOut": 0,
        "total_inProgress": 0
    }

    for row in query:
        if row.checkIn is None:
            stats["total_checkInOut"] += 1
            continue

        if row.checkOut is None:
            stats["total_inProgress"] += 1
            continue

        if row.examStartTime and row.checkIn <= row.examStartTime:
            stats["total_checkInOnTime"] += 1
        elif row.examStartTime:
            stats["total_checkInLate"] += 1

        if row.examEndTime and row.checkOut >= row.examEndTime:
            stats["total_checkOutOnTime"] += 1
        elif row.examEndTime:
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
        .filter(InvigilatorAttendance.invigilationStatus == True)
    )

    # Lecturer (Level 1) — see own only
    if user.userLevel == 1:
        query = query.filter(InvigilatorAttendance.invigilatorId == user.userId)

    # Dean, HOS, HOP (Level 2, 3, 4) — see all invigilations for courses under same department
    elif user.userLevel in [2, 3, 4]:
        query = query.filter(Course.courseDepartment == user.userDepartment)

    return query.order_by(Exam.examStatus.desc(), Exam.examStartTime.asc()).all()



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
    seen_exams = set()
    all_exam_dates = []

    for att in attendances:
        exam = att.report.exam
        if exam.examId in seen_exams:
            continue
        seen_exams.add(exam.examId)

        start_time = exam.examStartTime
        end_time = exam.examEndTime

        # ✅ Detect if exam spans multiple days (overnight)
        is_overnight = start_time.date() != end_time.date()

        # ✅ Helper function to build exam dictionary
        def exam_dict(start, end):
            return {
                "start_time": start,
                "end_time": end,
                "exam_id": exam.examId,
                "course_name": exam.course.courseName,
                "course_code": exam.course.courseCodeSectionIntake,
                "venue": exam.examVenue,
                "status": exam.examStatus,
                "is_overnight": is_overnight  # ✅ Mark overnight exams
            }

        # ✅ Handle overnight exams (spanning across midnight)
        if is_overnight:
            # --- Part 1: from start to midnight ---
            calendar_data[start_time.date()].append(
                exam_dict(
                    start_time,
                    datetime.combine(start_time.date(), datetime.max.time()).replace(hour=23, minute=59)
                )
            )
            all_exam_dates.append(start_time.date())

            # --- Part 2: from midnight to real end ---
            calendar_data[end_time.date()].append(
                exam_dict(
                    datetime.combine(end_time.date(), datetime.min.time()),
                    end_time
                )
            )
            all_exam_dates.append(end_time.date())
        else:
            # ✅ Normal same-day exam
            calendar_data[start_time.date()].append(exam_dict(start_time, end_time))
            all_exam_dates.append(start_time.date())

    # ✅ Create full date range for the entire year
    if all_exam_dates:
        year = min(all_exam_dates).year
    else:
        year = datetime.now().year

    full_dates = []
    current = datetime(year, 1, 1).date()
    while current.year == year:
        full_dates.append(current)
        current += timedelta(days=1)

    return calendar_data, full_dates



# -------------------------------
# Function for InviglationTimetable Route
# -------------------------------
@app.route('/user/invigilationTimetable', methods=['GET', 'POST'])
@login_required
def user_invigilationTimetable():
    calendar_data, full_dates = get_calendar_data()
    return render_template('user/userInvigilationTimetable.html', active_tab='user_invigilationTimetabletab', calendar_data=calendar_data, full_dates=full_dates)









@app.route('/user/ownTimetable', methods=['GET'])
@login_required
def user_ownTimetable():
    userId = session.get('user_id')
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

    return render_template('user/userOwnTimetable.html', active_tab='user_ownTimetabletab', timetable_rows=merged_timetable)






@app.route('/user/mergeTimetable', methods=['GET', 'POST'])
@login_required
def user_mergeTimetable():
    userId = session.get('user_id')

    # Get the logged-in user's department
    current_user = User.query.filter_by(userId=userId).first()
    if not current_user:
        flash("User not found.", "danger")
        return redirect(url_for('user_dashboard'))

    user_department = current_user.userDepartment

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

    # Build merged timetable list for rendering
    merged_timetable = []
    for item in merged.values():
        item['combined'] = list(zip(item['courseIntakes'], item['courseCodes'], item['courseSections']))
        merged_timetable.append(item)

    return render_template('user/userMergeTimetable.html', active_tab='user_mergeTimetabletab', timetable_rows=merged_timetable, department=user_department)







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



