import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Path to the Service Account JSON key file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
DRIVE_ROOT_ID = os.getenv('DRIVE_ROOT_ID')

# Ensure environment variables are set
assert SERVICE_ACCOUNT_FILE, "Environment variable SERVICE_ACCOUNT_FILE is not set."
assert DRIVE_ROOT_ID, "Environment variable DRIVE_ROOT_ID is not set."

# Scopes required by the Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Authenticate with Service Account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Google Drive API client
drive_service = build('drive', 'v3', credentials=credentials)

# Helper function to parse item name into structured format
def parse_item_name(item_name):
    try:
        # Extracting 'name', 'start', 'end', and 'technologies' from item name format
        name, date_range, technologies = item_name.split('|')
        start, end = date_range.split('-')
        tech_list = technologies.split('-')
        return {
            'start': start.strip(),
            'end': end.strip(),
            'name': name.strip(),
            'technologies': [tech.strip() for tech in tech_list]
        }
    except ValueError:
        # Handle unexpected formatting
        return None

# Helper function to download and clean text file content from Google Drive
def download_text_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    file_stream.seek(0)
    
    # Decode content and clean it
    content = file_stream.read().decode('utf-8')
    
    return content

# Helper function to list all files recursively with folder hierarchy
def list_all_files(service, folder_id=DRIVE_ROOT_ID, parent_path=''):
    projects_dict = {}
    folders_to_process = [{'id': folder_id, 'path': parent_path}]
    
    while folders_to_process:
        current_folder = folders_to_process.pop(0)
        folder_id = current_folder['id']
        folder_path = current_folder['path']
        
        # List files and folders in the current folder
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, mimeType)",
                spaces='drive'
            ).execute()
        except Exception as e:
            print(f"An error occurred while processing folder '{folder_path}': {e}")
            continue
        
        items = results.get('files', [])
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # If it's a folder, add to the processing queue with updated path
                folders_to_process.append({
                    'id': item['id'],
                    'path': f"{folder_path}/{item['name']}"
                })
            else:
                # Parse project information from the folder name
                parsed_data = parse_item_name(folder_path.split('/')[-1])
                if parsed_data:
                    project_name = parsed_data['name']
                    
                    # Initialize the project in the dictionary if it doesn't exist
                    if project_name not in projects_dict:
                        projects_dict[project_name] = {
                            **parsed_data,  # Add project details
                            'description': [],  # To be populated from description.txt
                            'buttons': [],
                            'videos': [],
                            'images': [],
                            'imageHeading': project_name,  # Use the project name as heading
                            'overview': True  # Set overview to True
                        }
                    
                    # Handle specific files: description.txt and link.txt
                    if item['name'] == 'Description.txt':
                        # Download the description content
                        description_content = download_text_file(service, item['id'])
                            # Split lines, remove \r and filter out empty lines
                        clean_content = [line.strip() for line in description_content.splitlines() if line.strip()]
                        projects_dict[project_name]['description'] = clean_content
                    elif item['name'] == 'link.txt':
                        # Download the link content and populate the buttons
                        link_content = download_text_file(service, item['id']).strip()
                        projects_dict[project_name]['buttons'] = [
                            {'text': 'link', 'link': link_content}
                        ]
                    # Append to either 'videos' or 'images' based on mimeType
                    elif 'video' in item['mimeType']:
                        # Create file URL
                        video_file_url = f"https://drive.google.com/file/d/{item['id']}/preview"
                        projects_dict[project_name]['videos'].append(video_file_url)
                    elif 'image' in item['mimeType']:
                        # Create file URL
                        image_file_url = f"https://drive.google.com/thumbnail?id={item['id']}&sz=w1000"
                        projects_dict[project_name]['images'].append(image_file_url)
                
    return list(projects_dict.values())

# List all files in Google Drive starting from the root folder
files = list_all_files(drive_service)

# Ensure the output directory exists
# os.makedirs('../src/data', exist_ok=True)

# Output the list to a JSON file
with open('../src/data/projects.json', 'w') as file:
    json.dump(files, file, indent=4)

print("Files listed and written to projects.json")
