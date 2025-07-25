import os
import requests
import json
from datetime import datetime
from security import decrypt_data

class MediumAPI:
    def __init__(self, access_token):
        if not access_token:
            raise ValueError("Medium access token is required.")
        self.access_token = access_token
        self.base_url = 'https://api.medium.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8'
        }

    def post_story(self, title, content, tags=None, publish_status='public'):
        """Publishes a new story to Medium."""
        if not title or not content:
            raise ValueError("Title and content are required for a Medium story.")

        # 1. Fetch authenticated user ID
        user_info_response = requests.get(f'{self.base_url}/me', headers=self.headers)
        user_info_response.raise_for_status()
        author_id = user_info_response.json()['data']['id']

        # 2. Post the story
        endpoint = f'{self.base_url}/users/{author_id}/posts'
        payload = {
            'title': title,
            'contentFormat': 'html',
            'content': content,
            'tags': tags or [],
            'publishStatus': publish_status,
        }
        
        response = requests.post(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

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

def post_to_medium(account, content, base_dir):
    """
    Main function to post content to Medium, using credentials from the database.
    """
    try:
        credentials = json.loads(decrypt_data(account['credentials']))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid credentials format for Medium account.")

    access_token = credentials.get('access_token')

    try:
        api = MediumAPI(access_token)
        
        title = content.get('title', 'No Title')
        description = content.get('description', '')
        hashtags = content.get('hashtags', '')

        # Construct HTML content for the post
        html_content = f"<h1>{title}</h1>\n<p>{description.replace('\n', '<br>')}</p>"
        if hashtags:
            formatted_tags = [f"#{tag.strip()}" for tag in hashtags.split(',') if tag.strip()]
            html_content += f"<p><em>{' '.join(formatted_tags)}</em></p>"
        
        tag_list = [tag.strip() for tag in hashtags.split(',') if tag.strip()]

        response = api.post_story(
            title=title,
            content=html_content,
            tags=tag_list[:5],
            publish_status='public'
        )
            
        print(f"[Medium API] Post successful: {response}")
        return response

    except Exception as e:
        raise Exception(f"Medium API Error: {e}") 