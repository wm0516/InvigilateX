import serial
import re
import requests
import time
from datetime import datetime, timezone

SERIAL_PORT = "COM5"
BAUD_RATE = 74880
LAST_SCAN_URL = "https://wm05.pythonanywhere.com/update-last-scan"

def extract_uid(line):
    match = re.search(r"UID:([0-9A-F ]+)", line)
    if match:
        return " ".join(match.group(1).strip().upper().split())
    return None

def read_rfid_continuously():
    print("🔌 Connecting to RFID reader...")

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {SERIAL_PORT}. Waiting for scans...")
    except Exception as e:
        print(f"❌ Failed to connect to {SERIAL_PORT}: {e}")
        return

    last_uid = None
    last_time = 0

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            uid = extract_uid(line)

            if uid:
                # Only trigger if it's a new card or after cooldown
                if uid != last_uid or (time.time() - last_time) > 2:
                    print(f"🪪 Card Detected: UID: {uid}")

                    try:
                        requests.post(LAST_SCAN_URL, json={
                            "cardNumber": uid,
                            "time": datetime.now(timezone.utc).isoformat()
                        }, timeout=3)
                        print("✅ Sent to Flask /update-last-scan")
                    except Exception as e:
                        print(f"⚠️ Could not update Flask: {e}")

                    # Update last UID + timestamp
                    last_uid = uid
                    last_time = time.time()

                    # ⏸ Wait until card is removed before scanning again
                    print("💨 Waiting for card removal...")
                    while True:
                        line2 = ser.readline().decode(errors="ignore").strip()
                        if not extract_uid(line2):  # No UID means card removed
                            print("💡 Card removed. Ready for next scan.")
                            break
                        time.sleep(0.1)

            time.sleep(0.05)

        except Exception as e:
            print(f"⚠️ Serial read error: {e}")
            time.sleep(1)

# ✅ Entry point
if __name__ == "__main__":
    read_rfid_continuously()
