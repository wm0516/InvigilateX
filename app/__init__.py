from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import threading

# --- Create the Flask application ---
app = Flask(__name__)

# --- Database configuration ---
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

# --- Email configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'minglw04@gmail.com'
app.config['MAIL_PASSWORD'] = 'jsco bvwc qpor fvku'
app.config['MAIL_DEFAULT_SENDER'] = 'minglw04@gmail.com'

# --- Initialize extensions ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

# --- Optional: Clean up any stale DB connections when the app starts ---
with app.app_context():
    db.session.remove()
    db.engine.dispose()

# --- RFID READER BACKGROUND THREAD ---
# This section integrates your rfid_bridge.py logic as a background service
try:
    from app.rfid_bridge import read_rfid_continuously
    def start_rfid_thread():
        """Start RFID background reader thread."""
        thread = threading.Thread(target=read_rfid_continuously, daemon=True)
        thread.start()
        print("🔁 RFID reader thread started and waiting for scans...")

    start_rfid_thread()
except Exception as e:
    print(f"⚠️ RFID reader could not be started: {e}")

# --- Import your route files (after app is ready) ---
try:
    from app import adminRoutes, userRoutes, authRoutes
    print("✅ Routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import routes: {e}")
