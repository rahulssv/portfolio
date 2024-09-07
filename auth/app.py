import os
from flask import Flask, redirect, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)

# Set environment variables for Google OAuth2 credentials
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/oauth2callback'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Custom OAuth2 Flow without credentials.json
def create_flow():
    return Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }, scopes=SCOPES)

# Start the OAuth flow
@app.route('/')
def auth():
    flow = create_flow()
    flow.redirect_uri = REDIRECT_URI
    authorization_url, _ = flow.authorization_url(prompt='consent')

    return redirect(authorization_url)

# Handle the OAuth2 callback
@app.route('/oauth2callback')
def oauth2callback():
    flow = create_flow()
    flow.redirect_uri = REDIRECT_URI
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials

    # Store credentials as needed or redirect to list files
    return redirect(f'/list-files?token={credentials.token}&refresh_token={credentials.refresh_token}')

# List all files in Google Drive root folder and export data in JSON format
@app.route('/list-files')
def list_files():
    # Use the credentials stored from the callback
    creds = Credentials.from_authorized_user_info({
        'token': request.args.get('token'),
        'refresh_token': request.args.get('refresh_token'),
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }, SCOPES)

    # Build the Google Drive API client
    drive_service = build('drive', 'v3', credentials=creds)

    # Replace 'your-folder-id-here' with the actual folder ID
    folder_id = '1-E_B0AXggAncRbl6vbs27yBiF1bMzUvZ'
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name)"
    ).execute()

    files = results.get('files', [])
    if not files:
        return jsonify({'message': 'No files found in your Google Drive root folder.'})

    # Return the file details as JSON
    return jsonify(files)

if __name__ == '__main__':
    app.run('localhost', 5000, debug=True)
