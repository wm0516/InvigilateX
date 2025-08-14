from flask import Flask, redirect, url_for, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import pathlib

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"  # Needed for sessions

# Path to downloaded credentials.json
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

@app.route('/')
def index():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    creds = Credentials(**session['credentials'])
    service = build('drive', 'v3', credentials=creds)
    
    # List files
    results = service.files().list(pageSize=50, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    # Update session credentials
    session['credentials'] = creds_to_dict(creds)
    
    file_list = '<br>'.join([f"{file['name']} ({file['id']})" for file in files])
    return f"<h1>Your Google Drive Files</h1><p>{file_list}</p>"

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=url_for('oauth2callback', _external=True, _scheme='https') + '?' +  request.query_string.decode())
    
    creds = flow.credentials
    session['credentials'] = creds_to_dict(creds)
    return redirect(url_for('index'))

def creds_to_dict(creds):
    return {'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes}

if __name__ == '__main__':
    app.run(debug=True)
