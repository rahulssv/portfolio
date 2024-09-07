import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Path to the Service Account JSON key file

SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
DRIVE_ROOT_ID = os.getenv('DRIVE_ROOT_ID')
# Scopes required by the Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Authenticate with Service Account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Google Drive API client
drive_service = build('drive', 'v3', credentials=credentials)

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

# List all files in Google Drive starting from the root folder
files = list_all_files(drive_service)

# Output the list to a JSON file
with open('documents.json', 'w') as file:
    json.dump(files, file, indent=4)

print("Files listed and written to auth.json")
