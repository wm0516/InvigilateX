from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler

# Create the Flask application
app = Flask(__name__)

# Database configuration
app.config['SECRET_KEY'] = '0efa50f2ad0a21e3fd7e7344d3e48380'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://WM05:Pythonanywhere@WM05.mysql.pythonanywhere-services.com/WM05$InvigilateX'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 200,
    'pool_pre_ping': True,
    'pool_size': 10,
    'max_overflow': 5,
}

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'minglw04@gmail.com'
app.config['MAIL_PASSWORD'] = 'jsco bvwc qpor fvku'
app.config['MAIL_DEFAULT_SENDER'] = 'minglw04@gmail.com'

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

# Background Scheduler
scheduler = BackgroundScheduler()

def scheduled_attendance_update():
    with app.app_context():
        # Import inside the function to avoid circular import
        from .authRoutes import update_attendanceStatus
        update_attendanceStatus()

# Schedule every 5 seconds
scheduler.add_job(func=scheduled_attendance_update, trigger='interval', seconds=5)
scheduler.start()

# Import routes AFTER app is created
from . import authRoutes, adminRoutes, userRoutes
