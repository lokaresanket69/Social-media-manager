from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import os
import json
import sqlite3
from security import decrypt_data

# Remove the local definition of BASE_DIR, it will be passed as an argument
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def post_to_youtube(account, content, base_dir):
    """
    Posts a video to YouTube using credentials stored in the database.
    """
    try:
        # The entire credentials object (including client_id, client_secret, refresh_token)
        # is stored as a JSON string in the database.
        creds_dict = json.loads(decrypt_data(account['credentials']))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid credentials format for YouTube account.")

    # Validate that the essential keys are present
    if not all(k in creds_dict for k in ['client_id', 'client_secret', 'refresh_token']):
         raise ValueError("YouTube credentials missing client_id, client_secret, or refresh_token.")

    try:
        # Create a Credentials object directly from the dictionary
        creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
        youtube = build('youtube', 'v3', credentials=creds)

        body = {
            'snippet': {
                'title': content['title'],
                'description': content['description'] or '',
                'tags': content['hashtags'].split() if content['hashtags'] else []
            },
            'status': {
                'privacyStatus': 'public' # or 'private', 'unlisted'
            }
        }

        media_path_absolute = os.path.join(base_dir, content['media_path'])
        if not os.path.exists(media_path_absolute):
            raise FileNotFoundError(f"Media file not found: {media_path_absolute}")

        media = MediaFileUpload(media_path_absolute, resumable=True)
        
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = request.execute()
        print(f"[YouTube API] Video uploaded successfully: {response}")
        return response

    except Exception as e:
        # If the credentials fail, it's good practice to log the specific error
        # without exposing the credentials themselves.
        print(f"[YouTube API] An error occurred during the API call: {e}")
        raise Exception(f"YouTube API Error: {e}")

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