
from flask import render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from collections import defaultdict
from app import app
from .authRoutes import login_required, user_homepage
from .backend import *
from .database import * 
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()



# -------------------------------
# Calculate Invigilation Stats (Filtered by User Department or Own Data)
# -------------------------------
def calculate_invigilation_stats(user):
    # Base query joining VenueSessionInvigilator -> VenueSession -> Exam -> Course -> Department
    query = VenueSessionInvigilator.query.join(VenueSession
        ).join(VenueExam, VenueExam.venueSessionId == VenueSession.venueSessionId
        ).join(Exam, VenueExam.examId == Exam.examId
        ).join(Course, Exam.examId == Course.courseExamId)

    if user.userRole in ["LECTURER", "PO", "LAB_ACC"]:
        # Only the user's own invigilation
        query = query.filter(VenueSessionInvigilator.invigilatorId == user.userId)
    elif user.userRole in ["DEAN", "HOP", "HOS"]:
        # All invigilations for courses under the same department
        query = query.join(Course.department).filter(Department.departmentCode == user.department.departmentCode)

    query = query.all()

    stats = {
        "total_report": len(query),
        "user_total_activeReport": 0,
        "total_checkInLate": 0,
        "total_checkOutEarly": 0,
    }

    for att in query:
        session_start = att.session.startDateTime if att.session else None
        session_end = att.session.endDateTime if att.session else None

        if not att.checkIn or not att.checkOut:
            stats["user_total_activeReport"] += 1
        if att.checkIn and session_start and att.checkIn > session_start:
            stats["total_checkInLate"] += 1
        if att.checkOut and session_end and att.checkOut < session_end:
            stats["total_checkOutEarly"] += 1

    return stats


# Lecturer get own
# DEAN, HOS, HOP get under own
# -------------------------------
# User: View Invigilation Report (Filtered by User Level)
# -------------------------------
@app.route('/user/invigilationReport', methods=['GET', 'POST'])
@login_required
def user_invigilationReport():
    current_user_id = session.get('user_id')
    user = User.query.get(current_user_id)
    if not check_access(current_user_id, "invigilationReport"):
        flash("Access denied", "error")
        return redirect(url_for("user_homepage"))


    # Base query joining VenueSessionInvigilator -> VenueSession -> VenueExam -> Exam -> Course
    vsi_query = (
        VenueSessionInvigilator.query
        .join(VenueSession, VenueSessionInvigilator.venueSessionId == VenueSession.venueSessionId)
        .join(VenueExam, VenueExam.venueSessionId == VenueSession.venueSessionId)
        .join(Exam, VenueExam.examId == Exam.examId)
        .join(Course, Exam.examId == Course.courseExamId)
        .join(User, VenueSessionInvigilator.invigilatorId == User.userId)
        .order_by(VenueSession.startDateTime, Course.courseCodeSectionIntake)
    )

    # Filter based on user level
    if user.userRole in ["LECTURER", "PO", "LAB_ASST"]:
        # Only show this user's invigilations
        vsi_query = vsi_query.filter(VenueSessionInvigilator.invigilatorId == user.userId)
    elif user.userRole in ["DEAN", "HOP", "HOS"]:
        # Show all invigilators for courses under the same department
        vsi_query = vsi_query.join(Course.department).filter(
            Department.departmentCode == user.department.departmentCode
        )

    vsi_entries = vsi_query.order_by(VenueSessionInvigilator.position.asc())

    # Group by venue + start/end time
    grouped_att = defaultdict(lambda: {"courses": [], "invigilators": []})
    for vsi in vsi_entries:
        if not vsi.session or not vsi.session.venue:
            continue

        key = (
            vsi.session.venue.venueNumber,
            vsi.session.startDateTime,
            vsi.session.endDateTime
        )

        # Add invigilator
        if vsi not in grouped_att[key]["invigilators"]:
            # For Lecturers only include themselves (safety)
            if user.userRole in ["LECTURER", "PO", "LAB_ASST"] and vsi.invigilatorId != user.userId:
                continue
            grouped_att[key]["invigilators"].append(vsi)

        # Add courses
        for ve in vsi.session.exams:
            if ve.exam and ve.exam.course:
                # For DEAN/HOP/HOS, only include courses in their department
                if user.userRole in ["DEAN", "HOP", "HOS"] and ve.exam.course.department.departmentCode != user.department.departmentCode:
                    continue
                course = {
                    "code": ve.exam.course.courseCodeSectionIntake,
                    "name": ve.exam.course.courseName
                }
                if course not in grouped_att[key]["courses"]:
                    grouped_att[key]["courses"].append(course)

    # Calculate stats
    stats = calculate_invigilation_stats(user)
    for vsi in vsi_entries:
        vsi.group_key = vsi.session.venueSessionId if vsi.session else None
        
    return render_template(
        'user/userInvigilationReport.html',
        active_tab='user_invigilationReporttab',
        attendances=vsi_entries,
        grouped_att=grouped_att,
        **stats,
        current_user=user
    )




def get_venue_calendar_data(userId):
    query = (VenueExam.query.join(Exam).join(VenueSession).join(Course))
    user = User.query.get_or_404(userId)

    # Case 1: Lecturer / PO / Lab Assistant
    if user.userRole in ["LECTURER", "PO", "LAB_ASST"]:
        query = (
            query
            .join(VenueSessionInvigilator,
                  VenueSessionInvigilator.venueSessionId == VenueSession.venueSessionId)
            .filter(
                or_(
                    VenueSessionInvigilator.invigilatorId == user.userId,
                    VenueSession.backupInvigilatorId == user.userId
                )
            )
        )

    # Case 2: Dean / HOP / HOS
    elif user.userRole in ["DEAN", "HOP", "HOS"]:
        query = query.filter(Course.courseDepartment == user.userDepartment)

    # Otherwise (admin, exam unit, etc.) → no filter
    venue_exams = query.all()

    # BUILD VENUE CALENDAR DATA
    venue_data = defaultdict(list)

    for ve in venue_exams:
        exam = ve.exam
        session = ve.session
        course = exam.course

        venue_data[session.venueNumber].append({
            "exam_id": exam.examId,
            "course_code": course.courseCodeSectionIntake,
            "course_name": course.courseName,
            "start_time": session.startDateTime,
            "end_time": session.endDateTime,
            "students": ve.studentCount,
            "total_invigilators": len(session.invigilators),
            "is_overnight": session.startDateTime.date() != session.endDateTime.date(),
        })

    # Sort exams per venue
    for venue in venue_data:
        venue_data[venue].sort(key=lambda x: x["start_time"])

    return dict(sorted(venue_data.items()))

# -------------------------------
# Function for InviglationTimetable Route
# -------------------------------
@app.route('/user/invigilationTimetable', methods=['GET', 'POST'])
@login_required
def user_invigilationTimetable():
    userId = session.get('user_id')
    if not check_access(userId, "invigilationTimetable"):
        flash("Access denied", "error")
        return redirect(url_for("user_homepage"))
    
    venue_data = get_venue_calendar_data(userId)
    return render_template('user/userInvigilationTimetable.html', active_tab='user_invigilationTimetabletab', venue_data=venue_data)


# -------------------------------
# Function for ViewOwnTimetable Route
# -------------------------------
@app.route('/user/ownTimetable', methods=['GET'])
@login_required
def user_ownTimetable():
    userId = session.get('user_id')
    if not check_access(userId, "timetable"):
        flash("Access denied", "error")
        return redirect(url_for("user_homepage"))
    
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
    if not check_access(userId, "timetable"):
        flash("Access denied", "error")
        return redirect(url_for("user_homepage"))

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
    if not check_access(userId, "staff"):
        flash("Access denied", "error")
        return redirect(url_for("user_homepage"))

    current_user = User.query.filter_by(userId=userId).first()
    if not current_user:
        flash("User not found.", "danger")
        return redirect(url_for('user_dashboard'))

    # Get all staff from the same department
    lecturers = (
        User.query
        .filter(
            User.userDepartment == current_user.userDepartment,
            User.userStatus.in_([1, 0, 2]))
        .order_by(User.userRole.asc(), User.userName.asc())
        .all()
    )
    # Counts filtered by department
    total_admin = User.query.filter_by(userRole="ADMIN").count()
    total_hop = User.query.filter_by(userRole="HOP").count()
    total_hos = User.query.filter_by(userRole="HOS").count()
    total_dean = User.query.filter_by(userRole="DEAN").count()
    total_lecturer = User.query.filter_by(userRole="LECTURER").count()
    total_po = User.query.filter_by(userRole="PO").count()
    total_lab_asst = User.query.filter_by(userRole="LAB_ASST").count()
    total_male_staff = User.query.filter_by(userGender=True).count()
    total_female_staff = User.query.filter_by(userGender=False).count()
    total_activated = User.query.filter_by(userStatus=1).count()
    total_deactivate = User.query.filter_by(userStatus=0).count()
    total_deleted = User.query.filter_by(userStatus=2).count()


    return render_template('user/userViewStaff.html', active_tab='user_viewStafftab',lecturers=lecturers,total_admin=total_admin,total_hop=total_hop,total_hos=total_hos,total_dean=total_dean,total_po=total_po, total_lab_asst=total_lab_asst,
        total_lecturer=total_lecturer,total_male_staff=total_male_staff,total_female_staff=total_female_staff,total_activated=total_activated,total_deactivate=total_deactivate,total_deleted=total_deleted)

# -------------------------------
# Function for Profile Route
# -------------------------------
@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    userId = session.get('user_id')
    if not check_access(userId, "profile"):
        flash("Access denied", "error")
        return redirect(url_for("user_homepage"))
    
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
            return redirect(url_for('user_profile'))

        # Update user info
        if valid and user:
            user.userContact = user_contact_text or None
            user.userCardId = user_cardUID or None
            if user_password1_text:
                hashed_pw = bcrypt.generate_password_hash(user_password1_text).decode('utf-8')
                user.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            record_action("UPDATE", "PROFILE", userId, userId)
            return redirect(url_for('user_profile'))

    return render_template('user/userProfile.html',active_tab='user_profiletab',user=user,user_contact_text=user_contact_text,
                           user_password1_text=user_password1_text,user_password2_text=user_password2_text,user_cardUID=user_cardUID)






