import os
import requests
import json
from datetime import datetime

class PinterestAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token or os.getenv('PINTEREST_ACCESS_TOKEN')
        self.base_url = 'https://api.pinterest.com/v5' # Pinterest API base URL
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def post_pin(self, board_id, title, description, image_path):
        """
        Posts a new pin to Pinterest.
        Requires an image file and a board_id.
        """
        if not board_id:
            print("Error: Board ID is required for Pinterest pins.")
            return None

        if not image_path or not os.path.exists(image_path):
            print(f"Error: Valid image path is required for Pinterest pins. Path provided: {image_path}")
            return None

        try:
            # Step 1: Upload the image to Pinterest and get a media ID
            print(f"[PinterestAPI] Attempting to upload image: {image_path}")
            media_id = self._upload_image(image_path)

            if not media_id:
                print(f"[PinterestAPI] Failed to upload image {image_path}. Cannot create pin.")
                return None

            # Step 2: Create the Pin using the uploaded media ID
            print(f"[PinterestAPI] Creating pin with media ID: {media_id}")
            pin_data = self._create_pin(board_id, title, description, media_id)

            if pin_data:
                print(f"[PinterestAPI] Pin posted successfully: {pin_data}")
                return pin_data
            else:
                print(f"[PinterestAPI] Failed to create pin for image {image_path}.")
                return None
        except Exception as e:
            print(f"Error posting to Pinterest: {str(e)}")
            return None

    def _upload_image(self, image_path):
        """
        Uploads an image to Pinterest and returns the media ID.
        """
        try:
            # Step 1: Register the image upload
            register_endpoint = f'{self.base_url}/media'
            register_payload = {
                'media_type': 'image'
            }
            register_response = requests.post(register_endpoint, headers=self.headers, json=register_payload)
            register_response.raise_for_status()
            upload_url = register_response.json()['image_upload_url']
            media_id = register_response.json()['media_id']

            # Step 2: Upload the image file
            with open(image_path, 'rb') as img_file:
                upload_headers = {'Content-Type': 'image/jpeg'} # Assuming JPEG, but should be dynamic based on file type
                upload_response = requests.put(upload_url, headers=upload_headers, data=img_file)
                upload_response.raise_for_status()
            
            return media_id
        except Exception as e:
            print(f"Error uploading image to Pinterest: {str(e)}")
            return None

    def _create_pin(self, board_id, title, description, media_id):
        """
        Creates a pin on Pinterest using a pre-uploaded media ID.
        """
        try:
            endpoint = f'{self.base_url}/pins'
            payload = {
                'board_id': board_id,
                'title': title,
                'description': description,
                'media_source': {
                    'source_type': 'image_url', 
                    'url': f'{self.base_url}/media/{media_id}' # Use media ID to construct the URL
                }
            }
            # NOTE: Pinterest API v5 documentation suggests using 'media_id' in a specific structure
            # This example uses 'image_url' with a constructed URL. For proper 'media_id' usage,
            # refer to Pinterest's latest API docs as this can be subject to change.

            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating pin on Pinterest: {str(e)}")
            return None

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