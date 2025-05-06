from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import pymysql

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()

# Create the Flask application
app = Flask(__name__)

# Application Configuration
app.config.update(
    SECRET_KEY='0efa50f2ad0a21e3fd7e7344d3e48380',
    SQLALCHEMY_DATABASE_URI='mysql+pymysql://wmm:Pythonanywhere@wmm.mysql.pythonanywhere-services.com:3306/wmm$InvigilateX_database?charset=utf8mb4',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_recycle': 299,
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 10,
        'connect_args': {'connect_timeout': 10}
    },
    UPLOAD_FOLDER='uploads',
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='minglw04@gmail.com',
    MAIL_PASSWORD='jsco bvwc qpor fvku',
    MAIL_DEFAULT_SENDER='minglw04@gmail.com'
)

# Initialize extensions with the app
db.init_app(app)
bcrypt.init_app(app)
mail.init_app(app)

# Database Connection Test
def test_database_connection():
    with app.app_context():
        try:
            conn = db.engine.connect()
            print("\033[92m" + "✓ Successfully connected to the database!" + "\033[0m")
            print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")
            conn.close()
            return True
        except Exception as e:
            print("\033[91m" + "✗ Database connection failed:" + "\033[0m")
            print(f"Error: {str(e)}")
            print("\nTroubleshooting Steps:")
            print("1. Verify your PythonAnywhere MySQL credentials")
            print("2. Check your IP is whitelisted in PythonAnywhere")
            print("3. Ensure your account allows external connections")
            print("4. Try connecting from a different network")
            return False

# Test the connection when starting the app
if __name__ == '__main__':
    if test_database_connection():
        print("Application is ready to run!")
    else:
        print("Fix database connection issues before proceeding")

# Import routes (must be after app creation to avoid circular imports)
from app import routes