from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
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


# Once login sucessful, it will kept all that user data and just use when need
@app.context_processor
def inject_dean_data():
    deanId = session.get('dean_id')
    if deanId:
        dean = User.query.get(deanId)
        if dean:
            return {
                'dean_id': deanId,
                'dean_name': dean.userName,
                'dean_department': dean.userDepartment,
                'dean_level': dean.userLevel,
                'dean_email': dean.userEmail,
                'dean_contact' : dean.userContact,
                'dean_status': dean.userStatus
            }
    return {
        'dean_id': None,
        'dean_name': '',
        'dean_department': '',
        'dean_level': '',
        'dean_email': '',
        'dean_contact': '' ,
        'dean_status': ''
    }


# home page (start with this!!!!!!!!!!!!!!)
@app.route('/deanHome', methods=['GET', 'POST'])
def dean_homepage():
    return render_template('deanPart/deanHomepage.html', active_tab='home')