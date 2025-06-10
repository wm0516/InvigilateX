from flask import Flask, request, jsonify, render_template_string
import secrets
import time
import qrcode
from io import BytesIO
import base64
import json

app = Flask(__name__)

# Mock user database (replace with real DB)
users = {
    "alice@example.com": {
        "public_key": "..."  # Store WebAuthn public key here
    }
}

# Store active challenges (replace with Redis in production)
active_challenges = {}

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <input id="userid" placeholder="Enter your email">
        <button onclick="startAuth()">Continue</button>
        <div id="qr-container"></div>
        <script src="/static/auth.js"></script>
    </body>
    </html>
    """

@app.route('/start-auth', methods=['POST'])
def start_auth():
    userid = request.json.get('userid')
    if userid not in users:
        return jsonify({"error": "User not found"}), 404

    # Generate a one-time challenge
    challenge = secrets.token_hex(32)
    expires_at = time.time() + 30  # 30s expiry

    active_challenges[challenge] = {
        "userid": userid,
        "expires_at": expires_at
    }

    # Create QR payload
    qr_payload = {
        "type": "webauthn",
        "challenge": challenge,
        "origin": "http://localhost:3000"  # Change to your domain
    }

    # Generate QR code
    img = qrcode.make(json.dumps(qr_payload))
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_b64 = base64.b64encode(buffered.getvalue()).decode()

    return jsonify({
        "qr": f"data:image/png;base64,{qr_b64}",
        "challenge": challenge
    })

@app.route('/verify-auth', methods=['POST'])
def verify_auth():
    challenge = request.json.get('challenge')
    signature = request.json.get('signature')  # Mocked for brevity

    if challenge not in active_challenges:
        return jsonify({"error": "Invalid or expired challenge"}), 400

    # Verify signature (in reality, use WebAuthn library)
    # Mock: Assume signature is valid
    userid = active_challenges[challenge]["userid"]
    del active_challenges[challenge]  # Consume challenge

    return jsonify({"status": "success", "userid": userid})

if __name__ == '__main__':
    app.run(debug=True)


async function startAuth() {
    const userid = document.getElementById('userid').value;
    const response = await fetch('/start-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userid })
    });

    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    // Show QR code
    const qrContainer = document.getElementById('qr-container');
    qrContainer.innerHTML = `<img src="${data.qr}" alt="Scan to login">`;

    // Poll for completion (replace with WebSockets in production)
    pollForAuth(data.challenge);
}

async function pollForAuth(challenge) {
    const checkAuth = async () => {
        const response = await fetch('/verify-auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ challenge })
        });
        const result = await response.json();

        if (result.status === 'success') {
            alert(`Logged in as ${result.userid}!`);
        } else {
            setTimeout(checkAuth, 1000);  // Retry every 1s
        }
    };
    checkAuth();
}

// Hypothetical phone-side JS (e.g., PWA)
const credential = await navigator.credentials.get({
    publicKey: {
        challenge: base64url.decode(qrPayload.challenge),
        rpId: new URL(qrPayload.origin).hostname,
        userVerification: "required"
    }
});