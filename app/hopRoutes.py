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



@app.route('/hopHome/timetables', methods=['GET', 'POST'])
def hop_timetable():
    # timetable = Invigilation.query.all()
    return render_template('hop/hopTimetable.html', active_tab='hop_timetabletab') #, timetable=timetable)

@app.route('/hopHome/invigilationReport', methods=['GET', 'POST'])
def hop_invigilationReport():
    return render_template('hop/hopInvigilationReport.html', active_tab='hop_invigilationReporttab')

@app.route('/hopHome/profile', methods=['GET', 'POST'])
def hop_profile():
    hopId = session.get('user_id')
    hop = User.query.filter_by(userId=hopId).first()
    
    # Pre-fill existing data
    hopContact_text = ''
    hopPassword1_text = ''
    hopPassword2_text = ''
    error_message = None

    if request.method == 'POST':
        hopContact_text = request.form.get('contact', '').strip()
        hopPassword1_text = request.form.get('password1', '').strip()
        hopPassword2_text = request.form.get('password2', '').strip()

        valid, message = check_profile(hopId, hopContact_text, hopPassword1_text, hopPassword2_text)
        if not valid:
            flash(message, 'error')
            return redirect(url_for('hop_profile'))

        if valid and hop:
            if hopContact_text:
                hop.userContact = hopContact_text
            if hopPassword1_text:
                hashed_pw = bcrypt.generate_password_hash(hopPassword1_text).decode('utf-8')
                hop.userPassword = hashed_pw

            db.session.commit()
            flash("Successfully updated", 'success')
            return redirect(url_for('hop_profile'))


    return render_template(
        'hop/hopProfile.html',
        active_tab='hop_profiletab',
        hop_name=hop.userName if hop else '',
        hop_id=hop.userId if hop else '',
        hop_email=hop.userEmail if hop else '',
        hop_department_text=hop.userDepartment if hop else '',
        hop_gender=hop.userGender if hop else '',
        hop_role_text={
            LECTURER: "Lecturer",
            HOP: "Hop",
            DEAN: "Dean",
            ADMIN: "Admin"
        }.get(hop.userLevel, "Unknown") if hop else '',
        hopContact_text=hopContact_text if hop else '',
        hopPassword1_text=hopPassword1_text,
        hopPassword2_text=hopPassword2_text,
        error_message=error_message
    )


