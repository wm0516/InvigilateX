
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

    stats = {
        "total_report": 0,
        "user_total_activeReport": 0,
        "total_checkInLate": 0,
        "total_checkOutEarly": 0,
    }

    # -------------------------------
    # LEVEL 1: Personal stats for lecturer
    # -------------------------------
    if user.userLevel == 1:
        # Total reports assigned to this user (any exam)
        stats["total_report"] = (
            InvigilationReport.query
            .join(InvigilatorAttendance, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
            .filter(InvigilatorAttendance.invigilatorId == user.userId)
            .filter(InvigilatorAttendance.invigilationStatus == True)
            .distinct()
            .count()
        )

        # Active reports for this user (examStatus == True)
        stats["user_total_activeReport"] = (
            InvigilationReport.query
            .join(InvigilatorAttendance, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
            .join(Exam, InvigilationReport.examId == Exam.examId)
            .filter(
                InvigilatorAttendance.invigilatorId == user.userId,
                InvigilatorAttendance.invigilationStatus == True,
                Exam.examStatus == True
            )
            .distinct()
            .count()
        )

        # Attendance stats (lateness / early checkout)
        records = (
            InvigilatorAttendance.query
            .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
            .join(Exam, InvigilationReport.examId == Exam.examId)
            .filter(
                InvigilatorAttendance.invigilatorId == user.userId,
                InvigilatorAttendance.invigilationStatus == True,
                Exam.examStatus == True
            )
            .all()
        )

    # -------------------------------
    # LEVEL 2-4: Department stats
    # -------------------------------
    else:
        # Total reports in department (all exams)
        stats["total_report"] = (
            InvigilationReport.query
            .join(Exam, InvigilationReport.examId == Exam.examId)
            .join(Course, Course.courseExamId == Exam.examId)
            .filter(Course.courseDepartment == user.userDepartment)
            .distinct()
            .count()
        )

        # Active reports in department (examStatus == True)
        stats["user_total_activeReport"] = (
            InvigilationReport.query
            .join(Exam, InvigilationReport.examId == Exam.examId)
            .join(Course, Course.courseExamId == Exam.examId)
            .filter(
                Course.courseDepartment == user.userDepartment,
                Exam.examStatus == True
            )
            .distinct()
            .count()
        )

        # Attendance stats (lateness / early checkout)
        records = (
            InvigilatorAttendance.query
            .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
            .join(Exam, InvigilationReport.examId == Exam.examId)
            .join(Course, Course.courseExamId == Exam.examId)
            .filter(
                Course.courseDepartment == user.userDepartment,
                InvigilatorAttendance.invigilationStatus == True,
                Exam.examStatus == True
            )
            .all()
        )

    # -------------------------------
    # Analyze lateness / early checkout
    # -------------------------------
    for r in records:
        if r.checkIn and r.checkIn > r.exam.examStartTime:
            stats["total_checkInLate"] += 1
        if r.checkOut and r.checkOut < r.exam.examEndTime:
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
    user = User.query.get(session.get('user_id'))
    if not user:
        return redirect(url_for('user_mergeTimetable'))
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
    return render_template('user/userInvigilationReport.html', active_tab='user_invigilationReporttab', attendances=attendances, **stats, current_user=user)
    
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
                "course_code": exam.course.courseCodeSectionIntake,
                "start_time": start,
                "end_time": end,
                "status": exam.examStatus,
                "is_overnight": is_overnight,
                "venue": venues,
            }

        if is_overnight:
            # Part 1: From start time to 23:59 on start day
            calendar_data[start_date].append(exam_dict(start_dt, datetime.combine(start_date, datetime.max.time()).replace(hour=23, minute=59)))
            # Part 2: From 00:00 on next day to end time
            calendar_data[end_date].append(exam_dict(datetime.combine(end_date, datetime.min.time()), end_dt))
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


    return render_template('user/userViewStaff.html', active_tab='user_viewStafftab',lecturers=lecturers,total_admin=total_admin,total_hop=total_hop,total_hos=total_hos,total_dean=total_dean,
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
    user_cardUID = user.userCardId or ''
    user_contact_text = user.userContact or ''
    user_password1_text = ''
    user_password2_text = ''

    if request.method == 'POST':
        user_cardUID = request.form.get('cardUID', '').strip().replace(' ', '')
        user_contact_text = request.form.get('contact', '').strip()
        user_password1_text = request.form.get('password1', '').strip()
        user_password2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(userId, user_cardUID, user_contact_text, user_password1_text, user_password2_text)
        if not valid:
            flash(message, 'error')
            return render_template('user/userProfile.html',active_tab='user_profiletab',user=user,user_contact_text=user_contact_text,
                                   user_password1_text=user_password1_text,user_password2_text=user_password2_text,user_cardUID=user_cardUID)

        # Update user info
        if user:
            user.userContact = user_contact_text or None
            user.userCardId = user_cardUID or None
            if user_password1_text:
                hashed_pw = bcrypt.generate_password_hash(user_password1_text).decode('utf-8')
                user.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('user_profile'))

    return render_template('user/userProfile.html',active_tab='user_profiletab',user=user,user_contact_text=user_contact_text,
                           user_password1_text=user_password1_text,user_password2_text=user_password2_text,user_cardUID=user_cardUID)

