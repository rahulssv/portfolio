import os
import json
from flask import Flask, redirect, request, jsonify, send_file
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)

# Set environment variables for Google OAuth2 credentials
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/oauth2callback'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_ROOT_ID = os.getenv('DRIVE_ROOT_ID')

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

# Helper function to list all files recursively with folder hierarchy
def list_all_files(service, folder_id=DRIVE_ROOT_ID, parent_path=''):
    files_list = []
    folders_to_process = [{'id': folder_id, 'path': parent_path}]
    
    while folders_to_process:
        current_folder = folders_to_process.pop(0)
        folder_id = current_folder['id']
        folder_path = current_folder['path']
        
        # List files and folders in the current folder
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name, mimeType)",
            spaces='drive'
        ).execute()
        
        items = results.get('files', [])
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # If it's a folder, add to the processing queue with updated path
                folders_to_process.append({
                    'id': item['id'],
                    'path': f"{folder_path}/{item['name']}"
                })
            else:
                # If it's a file, add to the list with full URL and folder path
                file_url = f"https://drive.google.com/uc?export=view&id={item['id']}"
                files_list.append({
                    'id': item['id'],
                    'name': item['name'],
                    'mimeType': item['mimeType'],
                    'url': file_url,
                    'folder': folder_path
                })
                
    return files_list

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

    # List all files starting from the root folder
    files = list_all_files(drive_service)

    if not files:
        return jsonify({'message': 'No files found in your Google Drive.'})

    # Write the file details to auth.json
    with open('documents.json', 'w') as file:
        json.dump(files, file, indent=4)
    
    # Send the file for download
    #send_file('auth.json', as_attachment=True)
    return jsonify(files)

if __name__ == '__main__':
    app.run('localhost', 5000, debug=True)
