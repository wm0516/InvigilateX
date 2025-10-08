# -------------------------------
# Third-party imports
# -------------------------------
from flask import render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer

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






@app.route('/lecturer/timetable', methods=['GET'])
@login_required
def lecturer_timetable():
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

    merged_timetable = list(merged.values())

    return render_template('lecturer/lecturerTimetable.html', active_tab='lecturer_timetabletab', timetable_rows=merged_timetable
)






@app.route('/lecturer/invigilationTimetable', methods=['GET', 'POST'])
@login_required
def lecturer_invigilationTimetable():
    return render_template('lecturer/lecturerInvigilationTimetable.html', active_tab='lecturer_invigilationTimetabletab')


@app.route('/lecturer/invigilationReport', methods=['GET', 'POST'])
@login_required
def lecturer_invigilationReport():
    return render_template('lecturer/lecturerInvigilationReport.html', active_tab='lecturer_invigilationReporttab')

@app.route('/lecturer/profile', methods=['GET', 'POST'])
@login_required
def lecturer_profile():
    lecturerId = session.get('user_id')
    lecturer = User.query.filter_by(userId=lecturerId).first()
    
    # Pre-fill existing data
    lecturerContact_text = ''
    lecturerPassword1_text = ''
    lecturerPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        lecturerContact_text = request.form.get('contact', '').strip()
        lecturerPassword1_text = request.form.get('password1', '').strip()
        lecturerPassword2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(lecturerId, lecturerContact_text, lecturerPassword1_text, lecturerPassword2_text)
        if not valid:
            flash(message, 'error')
            return redirect(url_for('lecturer_profile'))

        if valid and lecturer:
            if lecturerContact_text:
                lecturer.userContact = lecturerContact_text
            if lecturerPassword1_text:
                hashed_pw = bcrypt.generate_password_hash(lecturerPassword1_text).decode('utf-8')
                lecturer.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('lecturer_profile'))

    return render_template(
        'lecturer/lecturerProfile.html',
        active_tab='lecturer_profiletab',
        lecturer_name=lecturer.userName if lecturer else '',
        lecturer_id=lecturer.userId if lecturer else '',
        lecturer_email=lecturer.userEmail if lecturer else '',
        lecturer_department_text=lecturer.userDepartment if lecturer else '',
        lecturer_gender=lecturer.userGender if lecturer else '',
        lecturer_role_text={
            LECTURER: "LECTURER",
            HOP: "HOP",
            DEAN: "DEAN",
            ADMIN: "ADMIN"
        }.get(lecturer.userLevel, "Unknown") if lecturer else '',
        lecturer_contact_text=lecturer.userContact if lecturer else '',
        lecturerPassword1_text=lecturerPassword1_text,
        lecturerPassword2_text=lecturerPassword2_text,
        error_message=error_message
    )


