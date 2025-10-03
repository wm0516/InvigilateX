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


@app.route('/lecturer/timetable', methods=['GET', 'POST'])
@login_required
def lecturer_timetable():
    # timetable = Invigilation.query.all()
    return render_template('lecturer/lecturerTimetable.html', active_tab='lecturer_timetabletab') #, timetable=timetable)

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


