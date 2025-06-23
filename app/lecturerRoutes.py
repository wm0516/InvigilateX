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
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt()


@app.route('/lecturerHome/timetables', methods=['GET', 'POST'])
def lecturer_timetable():
    timetable = Invigilation.query.all()
    return render_template('lecturerPart/lecturerTimetable.html', active_tab='lecturer_timetabletab', timetable=timetable)

@app.route('/lecturerHome/invigilationTimetable', methods=['GET', 'POST'])
def lecturer_invigilationTimetable():
    return render_template('lecturerPart/lecturerInvigilationTimetable.html', active_tab='lecturer_invigilationTimetabletab')

@app.route('/lecturerHome/invigilationReport', methods=['GET', 'POST'])
def lecturer_invigilationReport():
    return render_template('lecturerPart/lecturerInvigilationReport.html', active_tab='lecturer_invigilationReporttab')

@app.route('/lecturerHome/profile', methods=['GET', 'POST'])
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
        is_valid, message = check_contact(lecturerContact_text)

        # Error checks
        if lecturerContact_text and not contact_format(lecturerContact_text):
            error_message = "Wrong Contact Number format"
        elif lecturerContact_text and not is_valid:
            error_message = message
        elif lecturerPassword1_text or lecturerPassword2_text:
            if lecturerPassword1_text != lecturerPassword2_text:
                error_message = "Passwords do not match."

        if error_message:
            flash(str(error_message), 'error')
        elif not lecturerContact_text and not lecturerPassword1_text:
            flash("Nothing to update", 'info')
        else:
            if lecturer:
                if lecturerContact_text:
                    lecturer.userContact = lecturerContact_text
                if lecturerPassword1_text:
                    hashed_pw = bcrypt.generate_password_hash(lecturerPassword1_text).decode('utf-8')
                    lecturer.userPassword = hashed_pw

                db.session.commit()
                flash("Successfully updated", 'success')
                return redirect(url_for('lecturer_profile'))

    return render_template(
        'lecturerPart/lecturerProfile.html',
        active_tab='lecturer_profiletab',
        lecturer_name=lecturer.userName if lecturer else '',
        lecturer_id=lecturer.userId if lecturer else '',
        lecturer_email=lecturer.userEmail if lecturer else '',
        lecturer_department_text=lecturer.userDepartment if lecturer else '',
        lecturerContact_text=lecturerContact_text,
        lecturerPassword1_text=lecturerPassword1_text,
        lecturerPassword2_text=lecturerPassword2_text,
        error_message=error_message
    )


