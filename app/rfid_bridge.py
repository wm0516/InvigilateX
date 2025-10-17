import serial
import requests
import re
from datetime import datetime, timezone

# --- CONFIGURATION ---
SERIAL_PORT = "COM5"   # Change to your Arduino port (check Arduino IDE → Tools → Port)
BAUD_RATE = 74880
FLASK_URL = "https://wm05.pythonanywhere.com/attendance"  # Your hosted Flask endpoint

# --- FUNCTION: Extract UID from serial line ---
def extract_uid(line):
    match = re.search(r"UID:([0-9A-F ]+)", line)
    if match:
        # e.g. "UID: F1 9A 69 1E" → keep spacing clean
        uid_raw = match.group(1).strip().upper()
        uid_formatted = " ".join(uid_raw.split())  # Ensures one space between bytes
        return uid_formatted
    return None

# --- MAIN LOOP ---
def main():
    print("🔌 Connecting to RFID reader...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {SERIAL_PORT}. Waiting for scans...\n")
    except Exception as e:
        print(f"❌ Could not connect to {SERIAL_PORT}: {e}")
        return

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if "UID:" in line:
            uid_spaced = extract_uid(line)
            if uid_spaced:
                print(f"🪪 Card Detected: UID: {uid_spaced}")

                payload = {
                    "cardNumber": uid_spaced,          # Compact format for Flask
                    "actionType": "checkin",             # Change to 'checkout' if needed
                    "clickTime": datetime.now(timezone.utc).isoformat()
                }

                try:
                    response = requests.post(FLASK_URL, json=payload, timeout=5)
                    data = response.json()
                    if data.get("success"):
                        remark = data.get("data", {}).get("remark", "No remark")
                        print(f"✅ Attendance success: {remark}\n")
                    else:
                        print(f"⚠️ Server response: {data.get('message', 'Unknown error')}\n")
                except Exception as e:
                    print(f"❌ Error sending to Flask: {e}\n")

if __name__ == "__main__":
    main()
