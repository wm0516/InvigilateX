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



@app.route('/deanHome/timetable', methods=['GET', 'POST'])
def dean_timetable():
    # timetable = Invigilation.query.all()
    return render_template('dean/deanTimetable.html', active_tab='dean_timetabletab') #, timetable=timetable)

@app.route('/deanHome/invigilationReport', methods=['GET', 'POST'])
def dean_invigilationReport():
    return render_template('dean/deanInvigilationReport.html', active_tab='dean_invigilationReporttab')

@app.route('/deanHome/profile', methods=['GET', 'POST'])
def dean_profile():
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
            return redirect(url_for('dean_profile'))

        if valid and dean:
            if deanContact_text:
                dean.userContact = deanContact_text
            if deanPassword1_text:
                hashed_pw = bcrypt.generate_password_hash(deanPassword1_text).decode('utf-8')
                dean.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('dean_profile'))

    return render_template(
        'dean/deanProfile.html',
        active_tab='dean_profiletab',
        dean_name=dean.userName if dean else '',
        dean_id=dean.userId if dean else '',
        dean_email=dean.userEmail if dean else '',
        dean_department_text=dean.userDepartment if dean else '',
        dean_gender=dean.userGender if dean else '',
        dean_role_text={
            LECTURER: "LECTURER",
            HOP: "HOP",
            DEAN: "DEAN",
            ADMIN: "ADMIN"
        }.get(dean.userLevel, "Unknown") if dean else '',
        dean_contact_text=dean.userContact if dean else '',
        deanPassword1_text=deanPassword1_text,
        deanPassword2_text=deanPassword2_text,
        error_message=error_message
    )


