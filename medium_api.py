import os
import requests
import json
from datetime import datetime

class MediumAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token or os.getenv('MEDIUM_ACCESS_TOKEN')
        self.base_url = 'https://api.medium.com/v1' # Placeholder API URL
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8'
        }

    def post_story(self, title, content, tags=None, publish_status='public'):
        """
        Publishes a new story to Medium.
        Requires Medium Integration Token.
        """
        if not title or not content:
            print("Error: Both title and content are required for posting a story to Medium.")
            return None

        try:
            # Fetch authenticated user ID to create a post under their account
            user_info_endpoint = f'{self.base_url}/me'
            user_info_response = requests.get(user_info_endpoint, headers=self.headers)
            user_info_response.raise_for_status()
            author_id = user_info_response.json()['data']['id']

            endpoint = f'{self.base_url}/users/{author_id}/posts'
            payload = {
                'title': title,
                'contentFormat': 'html', # Or 'markdown'
                'content': content, # Assuming content is already in desired format
                'tags': tags or [],
                'publishStatus': publish_status # e.g., 'public', 'draft', 'unlisted'
            }
            
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            print(f"[MediumAPI] Story posted successfully: {response.json()}")
            return response.json()
        except Exception as e:
            print(f"Error posting to Medium: {str(e)}")
            return None

    def schedule_story(self, title, content, scheduled_time, tags=None):
        """
        Schedules a story for later publication on Medium.
        NOTE: Medium's public API does not natively support scheduling posts directly.
        This function simulates scheduling by storing the post with a 'draft' status
        and relying on an external scheduler (like APScheduler in app.py) to change
        its status to 'public' at the scheduled_time.
        """
        print("\n--- Note: Medium API does not natively support scheduling. --- ")
        print("This function will post the story as a 'draft' and rely on the external scheduler.")
        # Post as draft, then the scheduler would need to update its status at scheduled_time
        return self.post_story(title, content, tags=tags, publish_status='draft') 