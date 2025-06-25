import os
import requests
import mimetypes
import json
from datetime import datetime
from security import decrypt_data

class PinterestAPI:
    def __init__(self, access_token):
        if not access_token:
            raise ValueError("Pinterest access token is required.")
        self.access_token = access_token
        self.base_url = 'https://api.pinterest.com/v5'
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def post_pin(self, board_id, title, description, image_path):
        """Posts a new pin to a specified Pinterest board."""
        if not board_id:
            raise ValueError("Board ID is required to post a pin.")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path does not exist: {image_path}")

        # 1. Upload the image to get a media ID
        media_id = self._upload_image(image_path)
        if not media_id:
            raise Exception("Failed to upload image to Pinterest.")

        # 2. Create the Pin using the uploaded media ID
        return self._create_pin(board_id, title, description, media_id)

    def _upload_image(self, image_path):
        """Uploads an image to Pinterest and returns the media ID."""
        endpoint = f'{self.base_url}/media'
        payload = {'media_type': 'image'}
        
        # Register the upload
        register_response = requests.post(endpoint, headers=self.headers, json=payload)
        register_response.raise_for_status()
        
        upload_data = register_response.json()
        upload_url = upload_data['upload_url']
        media_id = upload_data['media_id']

        # Upload the actual image file
        content_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
        upload_headers = {'Content-Type': content_type}
        
        with open(image_path, 'rb') as img_file:
            upload_response = requests.put(upload_url, headers=upload_headers, data=img_file)
            upload_response.raise_for_status()
        
        # Optionally, you might need to check the status of the media upload here
        # For simplicity, we assume it's ready.
        
        return media_id

    def _create_pin(self, board_id, title, description, media_id):
        """Creates a pin on Pinterest using a media ID."""
        endpoint = f'{self.base_url}/pins'
        payload = {
            'board_id': board_id,
            'title': title,
            'description': description,
            'media_source': {
                'source_type': 'media_id',
                'media_id': media_id
            }
        }
        
        response = requests.post(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def schedule_pin(self, board_id, title, description, image_path, scheduled_time):
        """
        Schedules a pin for later publication on Pinterest.
        NOTE: Pinterest's public API does not natively support direct post scheduling.
        This function simulates scheduling by relying on an external scheduler (like APScheduler in app.py).
        The actual posting will happen when the scheduler triggers `post_pin` at the scheduled_time.
        """
        print("\n--- Note: Pinterest API does not natively support scheduling. --- ")
        print("This function relies on the external scheduler to trigger the post_pin at the scheduled time.")
        # Simply return a success message or handle as a pending action
        # The actual scheduling logic is in scheduler.py
        return {'status': 'scheduled_via_external_scheduler', 'scheduled_time': scheduled_time.isoformat()}

def post_to_pinterest(account, content, base_dir):
    """
    Main function to post a pin to Pinterest, using credentials from the database.
    """
    try:
        credentials = json.loads(decrypt_data(account['credentials']))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid credentials format for Pinterest account.")

    access_token = credentials.get('access_token')
    board_id = credentials.get('board_id')

    if not board_id:
        raise ValueError("Pinterest Board ID is not configured for this account.")

    try:
        api = PinterestAPI(access_token)
        
        title = content.get('title', 'No Title')
        description = f"{content.get('description', '')}\n\n{content.get('hashtags', '')}".strip()
        media_path_relative = content.get('media_path')

        if not media_path_relative:
            raise ValueError("An image is required to post a pin to Pinterest.")

        media_path_absolute = os.path.join(base_dir, media_path_relative)
        
        response = api.post_pin(
            board_id=board_id,
            title=title,
            description=description,
            image_path=media_path_absolute
        )
            
        print(f"[Pinterest API] Pin created successfully: {response}")
        return response

    except Exception as e:
        raise Exception(f"Pinterest API Error: {e}") 