from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()

# Create the Flask app
app = Flask(__name__)

# Configure the app
app.config['SECRET_KEY'] = '0efa50f2ad0a21e3fd7e7344d3e48380'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://wmm:Pythonanywhere@wmm.mysql.pythonanywhere-services.com/wmm$InvigilateX_database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 200,
    'pool_pre_ping': True,
    'pool_size': 10,
    'max_overflow': 5
}
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'minglw04@gmail.com'
app.config['MAIL_PASSWORD'] = 'jsco bvwc qpor fvku'
app.config['MAIL_DEFAULT_SENDER'] = 'minglw04@gmail.com'

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True  # True in production (HTTPS)

# Initialize extensions with app
db.init_app(app)
bcrypt.init_app(app)
mail.init_app(app)

# Import routes at the bottom to avoid circular imports
from app import routes