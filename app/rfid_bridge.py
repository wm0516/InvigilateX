# app/rfid_reader.py
import serial
import threading
import re
import requests
from datetime import datetime, timezone

SERIAL_PORT = "COM5"
BAUD_RATE = 74880
FLASK_URL = "https://wm05.pythonanywhere.com/attendance"  # Local Flask endpoint

def extract_uid(line):
    match = re.search(r"UID:([0-9A-F ]+)", line)
    if match:
        uid_raw = match.group(1).strip().upper()
        uid_formatted = " ".join(uid_raw.split())
        return uid_formatted
    return None

def read_rfid_continuously():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {SERIAL_PORT}. Waiting for scans...")
    except Exception as e:
        print(f"❌ Could not connect to {SERIAL_PORT}: {e}")
        return

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if "UID:" in line:
                uid_spaced = extract_uid(line)
                if uid_spaced:
                    print(f"🪪 Card Detected: UID: {uid_spaced}")

                    payload = {
                        "cardNumber": uid_spaced,
                        "actionType": "checkin",  # or 'checkout' depending on mode
                        "clickTime": datetime.now(timezone.utc).isoformat()
                    }
                    try:
                        response = requests.post(FLASK_URL, json=payload, timeout=5)
                        print(f"📡 Sent to Flask, response: {response.text}")
                    except Exception as e:
                        print(f"❌ Error sending to Flask: {e}")
        except Exception as e:
            print(f"⚠️ Serial error: {e}")
