from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import os
import json
import sqlite3

# Remove the local definition of BASE_DIR, it will be passed as an argument
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def post_to_youtube(account, content, base_dir): # Accept base_dir here
    print(f"[YouTube API] Attempting to post content ID: {content['id']} for account: {account['name']}")
    
    # Load credentials
    cred_path_relative = account['credential_path']
    
    # Construct the absolute path using the passed base_dir
    cred_path_absolute = os.path.join(base_dir, cred_path_relative)
    
    creds = None
        
    print(f"[YouTube API] Loading credentials from: {cred_path_absolute}")
        
    if cred_path_absolute.endswith('.json'):
        try:
            creds = Credentials.from_authorized_user_file(cred_path_absolute, SCOPES)
            print("[YouTube API] Credentials loaded from .json file successfully.")
        except Exception as e:
            print(f"[YouTube API] Error loading credentials from .json file: {e}")
            # Update status to error in DB directly if credential loading fails
            try:
                conn = sqlite3.connect(os.path.join(base_dir, 'social_media_automation.db')) # Use base_dir for DB path
                conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (f"Error loading YouTube credentials: {e}", content['id']))
                conn.commit()
                conn.close()
            except Exception as db_e:
                print(f"[YouTube API] Error updating DB status after credential error: {db_e}")
            raise Exception(f"Error loading YouTube credentials: {e}")
    elif cred_path_absolute.endswith('.txt'):
        try:
            with open(cred_path_absolute) as f:
                token = f.read().strip()
            # Note: Using raw token like this is less reliable for long-term use than OAuth flow
            creds = Credentials(token, scopes=SCOPES)
            print("[YouTube API] Credentials loaded from .txt file (raw token).")
        except Exception as e:
            print(f"[YouTube API] Error loading credentials from .txt file: {e}")
            # Update status to error in DB directly
            try:
                conn = sqlite3.connect(os.path.join(base_dir, 'social_media_automation.db')) # Use base_dir for DB path
                conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (f"Error loading YouTube credentials: {e}", content['id']))
                conn.commit()
                conn.close()
            except Exception as db_e:
                print(f"[YouTube API] Error updating DB status after credential error: {db_e}")
            raise Exception(f"Error loading YouTube credentials: {e}")
    else:
        print("[YouTube API] Invalid credential file extension.")
        # Update status to error in DB directly
        try:
            conn = sqlite3.connect(os.path.join(base_dir, 'social_media_automation.db')) # Use base_dir for DB path
            conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (f"Invalid YouTube credential file extension: {cred_path_relative}", content['id']))
            conn.commit()
            conn.close()
        except Exception as db_e:
            print(f"[YouTube API] Error updating DB status after credential error: {db_e}")
        raise Exception('Invalid YouTube credential file: Must be .json or .txt')

    try:
        youtube = build('youtube', 'v3', credentials=creds)
        print("[YouTube API] YouTube service built successfully.")

        body = {
            'snippet': {
                'title': content['title'],
                'description': content['description'] or '',
                'tags': content['hashtags'].split() if content['hashtags'] else []
            },
            'status': {
                'privacyStatus': 'public'
            }
        }

        media_path_relative = content['media_path']
        # Construct the absolute path for the media file using the passed base_dir
        media_path_absolute = os.path.join(base_dir, media_path_relative)

        media = MediaFileUpload(media_path_absolute, resumable=True)
        print(f"[YouTube API] Media file loaded from: {media_path_absolute}")

        print("[YouTube API] Preparing API insert request...")
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        print("[YouTube API] Executing API request...")
        response = request.execute()
        print(f"[YouTube API] API response received: {response}")

        return response

    except Exception as e:
        print(f"[YouTube API] An error occurred during YouTube API call: {e}")
        # Update status to error in DB directly
        try:
            conn = sqlite3.connect(os.path.join(base_dir, 'social_media_automation.db')) # Use base_dir for DB path
            conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (str(e), content['id']))
            conn.commit()
            conn.close()
        except Exception as db_e:
            print(f"[YouTube API] Error updating DB status after API error: {db_e}")
        raise e # Re-raise the exception so the scheduler can catch it 