# app/rfid_bridge.py
import serial
import re
import requests
import time
from datetime import datetime, timezone

# --- Configuration ---
SERIAL_PORT = "COM5"             # Adjust this to your RFID COM port
BAUD_RATE = 74880
FLASK_URL = "https://wm05.pythonanywhere.com/attendance"   # Flask endpoint for attendance
LAST_SCAN_URL = "https://wm05.pythonanywhere.com/update-last-scan"  # New helper route

# --- Helper to extract UID from serial line ---
def extract_uid(line):
    match = re.search(r"UID:([0-9A-F ]+)", line)
    if match:
        uid_raw = match.group(1).strip().upper()
        # Format like "F1 9A 69 1E"
        uid_formatted = " ".join(uid_raw.split())
        return uid_formatted
    return None


def read_rfid_continuously():
    """Continuously read from the RFID serial port and send UID to Flask."""
    print("🔌 Connecting to RFID reader...")

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {SERIAL_PORT}. Waiting for scans...")
    except Exception as e:
        print(f"❌ Failed to connect to {SERIAL_PORT}: {e}")
        return

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if "UID:" in line:
                uid = extract_uid(line)
                if uid:
                    print(f"🪪 Card Detected: UID: {uid}")

                    # --- Optional: Update Flask /last-scan so HTML page shows it immediately ---
                    try:
                        requests.post(LAST_SCAN_URL, json={
                            "cardNumber": uid,
                            "time": datetime.now(timezone.utc).isoformat()
                        }, timeout=3)
                    except Exception as e:
                        print(f"⚠️ Could not update /last-scan: {e}")

                    # --- Send to Flask /attendance for check-in ---
                    payload = {
                        "cardNumber": uid,
                        "actionType": "checkin",  # Change to 'checkout' if in check-out mode
                        "clickTime": datetime.now(timezone.utc).isoformat()
                    }

                    try:
                        response = requests.post(FLASK_URL, json=payload, timeout=5)
                        print(f"📡 Sent to Flask, response: {response.text}")
                    except Exception as e:
                        print(f"❌ Error sending to Flask: {e}")

            time.sleep(0.2)  # Small delay to prevent CPU overuse

        except Exception as e:
            print(f"⚠️ Serial read error: {e}")
            time.sleep(1)
