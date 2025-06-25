import os
from datetime import datetime
import requests
from dotenv import load_dotenv
import json
from security import decrypt_data

load_dotenv()

class LinkedInAPI:
    def __init__(self, access_token, user_id):
        if not all([access_token, user_id]):
            raise ValueError("LinkedIn access token and user ID are required.")
        self.access_token = access_token
        self.user_id = user_id
        self.base_url = 'https://api.linkedin.com/v2'
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

    def post_text(self, text, visibility='PUBLIC'):
        """Post a text-only update to LinkedIn."""
        return self._post_ugc(text, visibility)

    def post_with_media(self, text, media_urn, visibility='PUBLIC', media_category='IMAGE'):
        """Post an update with media (image or video) to LinkedIn."""
        return self._post_ugc(text, visibility, media_urn, media_category)

    def _post_ugc(self, text, visibility, media_urn=None, media_category=None):
        """Helper method to make UGC (User Generated Content) posts."""
        endpoint = f"{self.base_url}/ugcPosts"
        share_content = {'shareCommentary': {'text': text}}

        if media_urn and media_category:
            share_content['shareMediaCategory'] = media_category
            share_content['media'] = [{'status': 'READY', 'media': media_urn}]
        else:
            share_content['shareMediaCategory'] = 'NONE'

        payload = {
            'author': f"urn:li:person:{self.user_id}",
            'lifecycleState': 'PUBLISHED',
            'specificContent': {'com.linkedin.ugc.ShareContent': share_content},
            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': visibility}
        }
        
        response = requests.post(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def upload_media(self, file_path, media_type='IMAGE'):
        """Upload media to LinkedIn and return the asset URN."""
        # 1. Register the upload
        register_endpoint = f"{self.base_url}/assets?action=registerUpload"
        recipe = 'urn:li:digitalmediaRecipe:feedshare-image' if media_type == 'IMAGE' else 'urn:li:digitalmediaRecipe:feedshare-video'
        
        register_payload = {
            'registerUploadRequest': {
                'recipes': [recipe],
                'owner': f"urn:li:person:{self.user_id}",
                'serviceRelationships': [{'relationshipType': 'OWNER', 'identifier': 'urn:li:userGeneratedContent'}]
            }
        }
        
        register_response = requests.post(register_endpoint, headers=self.headers, json=register_payload)
        register_response.raise_for_status()
        
        response_data = register_response.json()['value']
        upload_url = response_data['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn = response_data['asset']
        
        # 2. Upload the file
        with open(file_path, 'rb') as file:
            # Determine content type for the upload header
            content_type = 'image/jpeg'
            if file_path.lower().endswith('.png'):
                content_type = 'image/png'
            elif file_path.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif file_path.lower().endswith('.mp4'):
                 content_type = 'video/mp4'
            
            upload_headers = {'Content-Type': content_type}
            upload_response = requests.put(upload_url, headers=upload_headers, data=file)
            upload_response.raise_for_status()
        
        return asset_urn


def post_to_linkedin(account, content, base_dir):
    """
    Main function to post content to LinkedIn, using credentials from the database.
    """
    try:
        credentials = json.loads(decrypt_data(account['credentials']))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid credentials format for LinkedIn account.")
        
    access_token = credentials.get('access_token')
    user_id = credentials.get('user_id')

    try:
        api = LinkedInAPI(access_token, user_id)
        
        text_content = f"{content.get('title', '')}\n\n{content.get('description', '')}\n\n{content.get('hashtags', '')}".strip()
        media_path_relative = content.get('media_path')
        media_urn = None

        if media_path_relative:
            media_path_absolute = os.path.join(base_dir, media_path_relative)
            if os.path.exists(media_path_absolute):
                media_type = 'VIDEO' if media_path_absolute.lower().endswith('.mp4') else 'IMAGE'
                media_urn = api.upload_media(media_path_absolute, media_type=media_type)

        if media_urn:
            media_category = 'VIDEO' if 'video' in media_urn else 'IMAGE'
            response = api.post_with_media(text_content, media_urn, media_category=media_category)
        else:
            response = api.post_text(text_content)
            
        print(f"[LinkedIn API] Post successful: {response}")
        return response

    except Exception as e:
        raise Exception(f"LinkedIn API Error: {e}")

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