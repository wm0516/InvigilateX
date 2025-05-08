import re
from . import db
from flask_bcrypt import Bcrypt
from .database import *
from flask import redirect, url_for
bcrypt = Bcrypt()

 #from your_user_model import User  # replace with actual model import

'''def validate_user(username, password):
    user = User.query.filter_by(username=username).first()
    return user and user.check_password(password)

def create_user(userid, username, dept, email, contact, hashed_password):
    new_user = User(id=userid, username=username, department=dept, email=email, contact=contact, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()'''

# Email format
def email_format(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@newinti\.edu\.my$", email))

# Contact number format
def contact_format(contact):
    return bool(re.match(r"^01\d{8,9}$", contact))

# Password format
def password_format(password):
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,20}$", password))


def check_login(login_email, login_password):
    if not login_email or not login_password:
        return False, "Both fields are required."

    user = User.query.filter_by(email=login_email).first()

    if not user or not bcrypt.check_password_hash(user.password, login_password):
        return False, "Invalid Email address or password."

    return True, user.userid

# Staff Id format
# Pending


