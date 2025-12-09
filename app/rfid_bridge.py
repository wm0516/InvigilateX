import serial
import re
import requests
import time
from datetime import datetime, timezone

# Configuration
SERIAL_PORT = "COM7"
BAUD_RATE = 74880
FLASK_URL = "https://wm05.pythonanywhere.com/attendance"
LAST_SCAN_URL = "https://wm05.pythonanywhere.com/update-last-scan"

# Helper function: extract UID from serial line
def extract_uid(line):
    match = re.search(r"UID:([0-9A-F ]+)", line)
    if match:
        return " ".join(match.group(1).strip().upper().split())
    return None

# Continuous RFID reading loop
def read_rfid_continuously():
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

                    # Send UID to Flask endpoint
                    try:
                        requests.post(
                            LAST_SCAN_URL,
                            json={
                                "cardNumber": uid,
                                "time": datetime.now(timezone.utc).isoformat()
                            },
                            timeout=3
                        )
                        print("✅ Sent to Flask /update-last-scan")

                    except Exception as e:
                        print(f"⚠️ Could not update Flask: {e}")

                    time.sleep(0.2)

        except Exception as e:
            print(f"⚠️ Serial read error: {e}")
            time.sleep(1)

# Entry point
if __name__ == "__main__":
    read_rfid_continuously()
