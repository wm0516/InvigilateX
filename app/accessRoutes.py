from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from .backend import *
from .database import *
import os
from io import BytesIO
import pandas as pd
from werkzeug.utils import secure_filename
from .backend import *
from .database import *
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
from .authRoutes import login_required
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()


def get_all_attendances():
    dean = User.query.get(session.get('user_id'))
    return (
        InvigilatorAttendance.query
        .join(InvigilationReport, InvigilatorAttendance.reportId == InvigilationReport.invigilationReportId)
        .join(Exam, InvigilationReport.examId == Exam.examId)
        .join(User, InvigilatorAttendance.invigilatorId == User.userId)  # join to get the invigilator
        .filter(User.userDepartment == dean.userDepartment)
        .filter(InvigilatorAttendance.invigilationStatus == True)
        .all()
    )


@app.route('/access/invigilationReport', methods=['GET', 'POST'])
@login_required
def access_invigilationReport():
    attendances = get_all_attendances()
    return render_template('access/accessInvigilationReport.html', active_tab='access_invigilationReporttab', attendances=attendances)


@app.route('/access/ownTimetable', methods=['GET', 'POST'])
@login_required
def access_ownTimetable():
    deanId = session.get('user_id')
    timetable = Timetable.query.filter_by(user_id=deanId).first()
    timetable_rows = timetable.rows if timetable else []
    return render_template('access/accessOwnTimetable.html', active_tab='access_ownTimetabletab', timetable_rows=timetable_rows) #, timetable=timetable)


@app.route('/access/mergeTimetable', methods=['GET', 'POST'])
@login_required
def access_mergeTimetable():
    dean_id = session.get('user_id')
    dean_user = User.query.get(dean_id)
    
    # Get all timetables for users in the same department
    timetables = Timetable.query.join(User, Timetable.user_id == User.userId).filter(User.userDepartment == dean_user.userDepartment).all()
        
    # Flatten all rows into a single list
    timetable_rows = []
    for t in timetables:
        timetable_rows.extend(t.rows)
    
    return render_template('access/accessMergeTimetable.html', active_tab='access_mergeTimetabletab', timetable_rows=timetable_rows)



@app.route('/access/profile', methods=['GET', 'POST'])
@login_required
def access_profile():
    deanId = session.get('user_id')
    dean = User.query.filter_by(userId=deanId).first()
    
    # Pre-fill existing data
    deanContact_text = ''
    deanPassword1_text = ''
    deanPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        deanContact_text = request.form.get('contact', '').strip()
        deanPassword1_text = request.form.get('password1', '').strip()
        deanPassword2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(deanId, deanContact_text, deanPassword1_text, deanPassword2_text)
        if not valid:
            flash(message, 'error')
            return redirect(url_for('access_profile'))

        if valid and dean:
            if deanContact_text:
                dean.userContact = deanContact_text
            if deanPassword1_text:
                hashed_pw = bcrypt.generate_password_hash(deanPassword1_text).decode('utf-8')
                dean.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('access_profile'))

    return render_template(
        'access/accessProfile.html',
        active_tab='access_profiletab',
        dean_name=dean.userName if dean else '',
        dean_id=dean.userId if dean else '',
        dean_email=dean.userEmail if dean else '',
        dean_department_text=dean.userDepartment if dean else '',
        dean_gender=dean.userGender if dean else '',
        dean_role_text={
            LECTURER: "LECTURER",
            HOP: "HOP",
            HOS: "HOS",
            DEAN: "DEAN",
            ADMIN: "ADMIN"
        }.get(dean.userLevel, "Unknown") if dean else '',
        dean_contact_text=dean.userContact if dean else '',
        deanPassword1_text=deanPassword1_text,
        deanPassword2_text=deanPassword2_text,
        error_message=error_message
    )


