from apscheduler.schedulers.background import BackgroundScheduler
from app import app
from app.backend import send_invigilator_slot_notifications_for_all
from datetime import datetime

def job():
    print(f"Running scheduled job at {datetime.now()}")
    results = send_invigilator_slot_notifications_for_all()
    print(results)

if __name__ == "__main__":
    scheduler = BackgroundScheduler(timezone="Asia/Kuala_Lumpur")
    # Run every day at 18:30 for example
    scheduler.add_job(job, 'cron', hour=18, minute=30)

    scheduler.start()

    print("Scheduler started. Press Ctrl+C to exit.")
    try:
        # Keep the script running
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
