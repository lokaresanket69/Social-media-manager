import os
from datetime import datetime
import requests
from dotenv import load_dotenv
import json
from security import decrypt_data

load_dotenv()

class LinkedInAPI:
    def __init__(self, access_token, user_id):
        self.access_token = access_token
        self.user_id = user_id
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json',
            'LinkedIn-Version': '202402'
        }
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up a logger for the LinkedIn API client."""
        import logging
        logger = logging.getLogger('linkedin_api')
        logger.setLevel(logging.DEBUG)
        
        # Create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Add the handlers to the logger
        if not logger.handlers:  # Avoid adding handlers multiple times
            logger.addHandler(ch)
            
        return logger
        
    def _make_request(self, method, endpoint, json_data=None, params=None, headers=None, is_upload=False):
        """Helper method to make HTTP requests with proper error handling and logging."""
        url = f"{self.base_url}{endpoint}"
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
            
        # Log the request (without sensitive data)
        log_data = {
            'method': method,
            'url': url,
            'has_json': json_data is not None,
            'params': params
        }
        self.logger.debug(f"Making request: {log_data}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                headers=request_headers,
                timeout=30
            )
            
            # Log the response status and headers
            self.logger.debug(f"Response status: {response.status_code}")
            
            # Try to parse JSON if possible
            response_data = None
            try:
                if response.text:
                    response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text
                
            # Log error responses
            if response.status_code >= 400:
                error_msg = f"LinkedIn API error ({response.status_code}): {response.text}"
                self.logger.error(error_msg)
                
                # Handle specific error cases
                if response.status_code == 401:
                    raise ValueError("Invalid or expired access token. Please re-authenticate your LinkedIn account.")
                elif response.status_code == 403:
                    # Check if it's a permission issue
                    if "Not enough permissions" in response.text:
                        raise ValueError("Insufficient permissions. Please ensure your LinkedIn app has the 'w_member_social' permission.")
                
                # Raise a general error for other cases
                response.raise_for_status()
                
            return response_data or response.text
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request to LinkedIn API failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e

    def post_text(self, text, visibility='PUBLIC'):
        """Post a text-only update to LinkedIn."""
        return self._post_ugc(text, visibility)

    def post_with_media(self, text, media_urn, visibility='PUBLIC', media_category='IMAGE'):
        """Post an update with media (image or video) to LinkedIn."""
        return self._post_ugc(text, visibility, media_urn, media_category)

    def _post_ugc(self, text, visibility, media_urn=None, media_category=None):
        """Helper method to make UGC (User Generated Content) posts."""
        endpoint = "/ugcPosts"  # Just the endpoint path, base_url is already set
        share_content = {'shareCommentary': {'text': text}}

        if media_urn and media_category:
            share_content['shareMediaCategory'] = media_category
            share_content['media'] = [{'status': 'READY', 'media': media_urn}]
            print(f"[LinkedIn API] Posting with media category: {media_category}")
        else:
            share_content['shareMediaCategory'] = 'NONE'
            print(f"[LinkedIn API] Posting text-only content")

        payload = {
            'author': f"urn:li:person:{self.user_id}",
            'lifecycleState': 'PUBLISHED',
            'specificContent': {'com.linkedin.ugc.ShareContent': share_content},
            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': visibility}
        }
        
        print(f"[LinkedIn API] Final payload: {json.dumps(payload, indent=2)}")
        return self._make_request('POST', endpoint, json_data=payload)


def post_to_linkedin(account, content, base_dir):
    """
    Main function to post content to LinkedIn, using credentials from the database.
    """
    try:
        # Support both sqlite3.Row and dict for both account and content
        if not isinstance(account, dict):
            account = dict(account)
        if not isinstance(content, dict):
            content = dict(content)
        
        print(f"[LinkedIn] Starting post process for content ID: {content.get('id')}")
        
        # Decrypt and parse credentials
        credentials = json.loads(decrypt_data(account.get('credentials', '{}')))
        if not credentials or 'access_token' not in credentials:
            raise ValueError("Invalid or missing LinkedIn credentials")
                
        access_token = credentials.get('access_token')
        person_urn = credentials.get('person_urn')
        
        # Log basic info (without sensitive data)
        print(f"[LinkedIn] Processing post for account: {account.get('name')}")
        print(f"[LinkedIn] Person URN: {'Found' if person_urn else 'Not found'}")
        
        # Extract user ID from person URN if available
        user_id = None
        if person_urn and person_urn.startswith('urn:li:person:'):
            user_id = person_urn.split(':')[-1]
        
        if not user_id:
            # Try to get user ID from the API if not in credentials
            try:
                print("[LinkedIn] No user ID found in credentials, fetching from API...")
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'X-Restli-Protocol-Version': '2.0.0'
                }
                response = requests.get(
                    'https://api.linkedin.com/v2/me',
                    headers=headers,
                    timeout=30
                )
                if response.status_code == 200:
                    user_data = response.json()
                    user_id = user_data.get('id')
                    print(f"[LinkedIn] Retrieved user ID from API: {user_id}")
            except Exception as e:
                print(f"[LinkedIn] Error fetching user ID: {str(e)}")
        
        if not user_id:
            raise ValueError("Could not determine LinkedIn user ID. Please re-authenticate your account.")
        
        # Check if token is expired
        expires_at = credentials.get('expires_at')
        if expires_at:
            from datetime import datetime, timezone
            try:
                # Ensure both datetimes are timezone-aware
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                current_dt = datetime.now(timezone.utc)
                
                # If expires_dt is naive, make it timezone-aware
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                
                if current_dt > expires_dt:
                    error_msg = "LinkedIn access token has expired. Please re-authenticate your account."
                    print(f"[LinkedIn] {error_msg}")
                    raise ValueError(error_msg)
            except (ValueError, AttributeError) as e:
                print(f"[LinkedIn] Error checking token expiration: {str(e)}")
        else:
            print("[LinkedIn] No expiration time found for access token")
            
        # Check if we have the required scopes
        required_scopes = {'w_member_social'}
        # Robust: handle both list and string
        raw_scopes = credentials.get('scopes', [])
        if isinstance(raw_scopes, str):
            token_scopes = set(raw_scopes.split())
        elif isinstance(raw_scopes, list):
            token_scopes = set(raw_scopes)
        else:
            token_scopes = set()
        print(f"[LinkedIn] Token scopes for account {account.get('name')}: {token_scopes}")
        missing_scopes = required_scopes - token_scopes
        if missing_scopes:
            error_msg = f"Missing required LinkedIn OAuth scopes: {', '.join(missing_scopes)}. Please re-authenticate with the correct permissions."
            print(f"[LinkedIn] {error_msg}")
            raise ValueError(error_msg)
            
    except requests.exceptions.RequestException as e:
        error_msg = f"[LinkedIn] Network error while connecting to LinkedIn API: {str(e)}"
        print(error_msg)
        raise Exception(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"[LinkedIn] Failed to parse LinkedIn API response: {str(e)}"
        print(error_msg)
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"[LinkedIn] Error in post_to_linkedin: {str(e)}"
        print(error_msg)
        raise Exception(error_msg) from e
    
    try:
        api = LinkedInAPI(access_token, user_id)
        text_content = f"{content.get('title', '')}\n\n{content.get('description', '')}\n\n{content.get('hashtags', '')}".strip()
        media_path_relative = content.get('media_path')
        media_urn = None
        if media_path_relative:
            media_path_absolute = os.path.join(base_dir, media_path_relative)
            if os.path.exists(media_path_absolute):
                # Check for video file extensions
                video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv']
                is_video = any(media_path_absolute.lower().endswith(ext) for ext in video_extensions)
                media_type = 'VIDEO' if is_video else 'IMAGE'
                print(f"[LinkedIn API] Detected media type: {media_type} for file: {media_path_absolute}")
                media_urn = api.upload_media(media_path_absolute, media_type=media_type)
        # Log the request payload
        print(f"[LinkedIn API] Request payload: {text_content}")
        if media_urn:
            # Determine media category based on the actual media type, not the URN
            media_category = 'VIDEO' if media_type == 'VIDEO' else 'IMAGE'
            print(f"[LinkedIn API] Posting with media: {media_urn}, category: {media_category}")
            try:
                response = api.post_with_media(text_content, media_urn, media_category=media_category)
            except requests.HTTPError as http_err:
                # If permissions error, retry as text-only
                if http_err.response.status_code == 403:
                    print("[LinkedIn API] 403 when posting with media – falling back to text-only post.")
                    response = api.post_text(text_content)
                else:
                    raise
        else:
            print(f"[LinkedIn API] Posting text-only update.")
            response = api.post_text(text_content)
        print(f"[LinkedIn API] Post successful: {response}")
        return response
    except requests.HTTPError as http_err:
        print(f"[LinkedIn API] HTTPError: {http_err.response.status_code} {http_err.response.text}")
        raise Exception(f"LinkedIn API Error: {http_err.response.status_code} {http_err.response.text}")
    except Exception as e:
        print(f"[LinkedIn API] Exception: {e}")
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