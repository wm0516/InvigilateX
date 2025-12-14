from app import app
from backend import send_invigilator_slot_notifications_for_all

if __name__ == "__main__":
    with app.app_context():
        send_invigilator_slot_notifications_for_all()
