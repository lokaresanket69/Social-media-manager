import os
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

class LinkedInAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token or os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.base_url = 'https://api.linkedin.com/v2'
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

    def post_content(self, text, visibility='PUBLIC', media_urn=None):
        """
        Post content to LinkedIn
        """
        if not text:
            print("Error: Text content is required for posting to LinkedIn.")
            return None

        try:
            endpoint = f"{self.base_url}/ugcPosts"
            share_content = {
                'shareCommentary': {
                    'text': text
                },
                'shareMediaCategory': 'NONE'
            }

            if media_urn:
                share_content['shareMediaCategory'] = 'IMAGE' # Or 'VIDEO' if applicable
                share_content['media'] = [{
                    'status': 'READY',
                    'media': media_urn
                }]

            payload = {
                'author': f"urn:li:person:{os.getenv('LINKEDIN_USER_ID')}",
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': share_content
                },
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': visibility
                }
            }
            
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error posting to LinkedIn: {str(e)}")
            return None

    def schedule_post(self, text, scheduled_time, visibility='PUBLIC'):
        """
        Schedule a post for later
        """
        try:
            endpoint = f"{self.base_url}/scheduledPosts"
            payload = {
                'author': f"urn:li:person:{os.getenv('LINKEDIN_USER_ID')}",
                'lifecycleState': 'SCHEDULED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {
                            'text': text
                        },
                        'shareMediaCategory': 'NONE'
                    }
                },
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': visibility
                },
                'scheduledTime': int(scheduled_time.timestamp() * 1000)
            }
            
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error scheduling LinkedIn post: {str(e)}")
            return None

    def get_scheduled_posts(self):
        """
        Get all scheduled posts
        """
        try:
            endpoint = f"{self.base_url}/scheduledPosts"
            params = {
                'q': 'author',
                'author': f"urn:li:person:{os.getenv('LINKEDIN_USER_ID')}"
            }
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting scheduled LinkedIn posts: {str(e)}")
            return None

    def upload_media(self, file_path, media_type='IMAGE'):
        """
        Upload media to LinkedIn
        """
        try:
            # First, register the upload
            register_endpoint = f"{self.base_url}/assets?action=registerUpload"
            register_payload = {
                'registerUploadRequest': {
                    'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                    'owner': f"urn:li:person:{os.getenv('LINKEDIN_USER_ID')}",
                    'serviceRelationships': [{
                        'relationshipType': 'OWNER',
                        'identifier': 'urn:li:userGeneratedContent'
                    }]
                }
            }
            
            register_response = requests.post(
                register_endpoint,
                headers=self.headers,
                json=register_payload
            )
            register_response.raise_for_status()
            upload_url = register_response.json()['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset = register_response.json()['value']['asset']
            
            # Then, upload the file
            with open(file_path, 'rb') as file:
                upload_response = requests.put(
                    upload_url,
                    headers={'Content-Type': 'image/jpeg'},
                    data=file
                )
                upload_response.raise_for_status()
            
            return asset
        except Exception as e:
            print(f"Error uploading media to LinkedIn: {str(e)}")
            return None 