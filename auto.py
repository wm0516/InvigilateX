from app import app
from app.backend import send_invigilator_slot_notifications_for_all

if __name__ == "__main__":
    with app.app_context():
        results = send_invigilator_slot_notifications_for_all()
        print(results)  # <-- add this line to see which emails were sent