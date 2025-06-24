import os
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

class QuoraAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token or os.getenv('QUORA_ACCESS_TOKEN')
        self.base_url = 'https://api.quora.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def post_content(self, title, content, topics=None, image_path=None):
        """
        Post content to Quora
        """
        if not title or not content:
            print("Error: Both title and content are required for posting to Quora.")
            return None

        try:
            endpoint = f"{self.base_url}/answers"
            payload = {
                'title': title,
                'content': content,
                'topics': topics or []
            }
            
            if image_path:
                print(f"Warning: Quora's public API does not natively support direct image uploads to posts/answers.")
                print(f"Image '{image_path}' will not be directly attached. Consider hosting externally and embedding URL in content.")

            # This request will send the text content. Image handling is external/conceptual.
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error posting to Quora: {str(e)}")
            return None

    def schedule_post(self, title, content, scheduled_time, topics=None):
        """
        Schedule a post for later
        """
        try:
            endpoint = f"{self.base_url}/scheduled_posts"
            payload = {
                'title': title,
                'content': content,
                'scheduled_time': scheduled_time.isoformat(),
                'topics': topics or []
            }
            
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error scheduling Quora post: {str(e)}")
            return None

    def get_scheduled_posts(self):
        """
        Get all scheduled posts
        """
        try:
            endpoint = f"{self.base_url}/scheduled_posts"
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting scheduled Quora posts: {str(e)}")
            return None 