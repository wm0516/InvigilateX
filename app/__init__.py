from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import pymysql
from .database import *

print("1")

# Create the Flask application
app = Flask(__name__)

print("3")



# database password: Pythonanywhere 

app.config['SECRET_KEY'] = '0efa50f2ad0a21e3fd7e7344d3e48380'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://WM05:Pythonanywhere@WM05.mysql.pythonanywhere-services.com/WM05$InvigilateX'
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


print("4")
# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
print("5")

# Database Connection Test
def test_database_connection():
    print("6")
    with app.app_context():
        try:
            print("7")
            print("Hi database")
            conn = db.engine.connect()
            print("connected")
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
        
print("8")

# Test the connection when starting the app
# if __name__ == '__main__':
with app.app_context():
    print("9")
    if test_database_connection():
        print("Application is ready to run!")
    else:
        print("Fix database connection issues before proceeding")

print("10. After __main__ check")  # Debug point 10

# Import routes (must be after app creation to avoid circular imports)
try:
    from app import routes
    print("11. Routes imported successfully")  # Debug point 11
except ImportError as e:
    print(f"12. Failed to import routes: {e}")  