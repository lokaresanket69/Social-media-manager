import os
import json
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from security import encrypt_data

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def process_youtube_credentials(credentials_json, account_name):
    """
    Process YouTube credentials from a JSON file and return ready-to-use credentials.
    This handles the entire OAuth flow automatically.
    """
    try:
        # Parse the uploaded JSON file
        if isinstance(credentials_json, str):
            creds_data = json.loads(credentials_json)
        else:
            creds_data = credentials_json
            
        # Check if it's a credentials file or a token file
        if 'installed' in creds_data:
            # This is a credentials file, we need to do OAuth flow
            return handle_oauth_flow(creds_data, account_name)
        elif 'client_id' in creds_data and 'client_secret' in creds_data:
            # This might be a credentials file or already have tokens
            if 'refresh_token' in creds_data:
                # Already has tokens, just validate
                return validate_and_return_credentials(creds_data, account_name)
            else:
                # Need to do OAuth flow
                return handle_oauth_flow(creds_data, account_name)
        else:
            raise ValueError("Invalid YouTube credentials format")
            
    except Exception as e:
        raise Exception(f"Failed to process YouTube credentials: {str(e)}")

def handle_oauth_flow(creds_data, account_name):
    """
    Handle the OAuth flow to get refresh token
    """
    try:
        # Create a temporary credentials file for the OAuth flow
        temp_creds_file = f"temp_creds_{account_name}.json"
        with open(temp_creds_file, 'w') as f:
            json.dump(creds_data, f)
        
        # Determine if it's web or installed app
        is_web_app = 'web' in creds_data or ('installed' not in creds_data and 'web' not in creds_data)
        
        if is_web_app:
            # For web applications, we need to use a different approach
            # We'll use the web flow with a local server
            from google_auth_oauthlib.flow import Flow
            
            # Create flow for web application
            flow = Flow.from_client_secrets_file(
                temp_creds_file,
                scopes=SCOPES,
                redirect_uri='http://localhost:8080/'
            )
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"[YouTube Auth] Please visit this URL to authorize: {auth_url}")
            print("[YouTube Auth] After authorization, you'll be redirected to localhost:8080")
            print("[YouTube Auth] Copy the 'code' parameter from the URL and paste it here:")
            
            # Get authorization code from user
            auth_code = input("Enter the authorization code: ").strip()
            
            # Exchange code for tokens
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
        else:
            # For installed applications, use the standard flow
            flow = InstalledAppFlow.from_client_secrets_file(temp_creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Clean up temp file
        os.remove(temp_creds_file)
        
        # Convert to dictionary format
        creds_dict = {
            'client_id': creds_data.get('web', {}).get('client_id') or creds_data.get('installed', {}).get('client_id') or creds_data.get('client_id'),
            'client_secret': creds_data.get('web', {}).get('client_secret') or creds_data.get('installed', {}).get('client_secret') or creds_data.get('client_secret'),
            'refresh_token': creds.refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token'
        }
        
        # Validate the credentials
        return validate_and_return_credentials(creds_dict, account_name)
        
    except Exception as e:
        # Clean up temp file if it exists
        if os.path.exists(temp_creds_file):
            os.remove(temp_creds_file)
        raise Exception(f"OAuth flow failed: {str(e)}")

def validate_and_return_credentials(creds_dict, account_name):
    """
    Validate credentials and return them in the correct format
    """
    try:
        # Create credentials object
        creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
        
        # Test the credentials by making a simple API call
        youtube = build('youtube', 'v3', credentials=creds)
        channels_response = youtube.channels().list(mine=True, part='snippet').execute()
        
        if not channels_response.get('items'):
            raise Exception("No YouTube channels found for this account")
        
        # Get channel info
        channel = channels_response['items'][0]
        channel_name = channel['snippet']['title']
        
        # Add channel info to credentials
        creds_dict['channel_name'] = channel_name
        creds_dict['channel_id'] = channel['id']
        
        print(f"[YouTube Auth] Successfully authenticated channel: {channel_name}")
        
        # Encrypt and return
        encrypted_creds = encrypt_data(json.dumps(creds_dict))
        return {
            'credentials': encrypted_creds,
            'name': f"{account_name} ({channel_name})",
            'channel_info': {
                'name': channel_name,
                'id': channel['id']
            }
        }
        
    except Exception as e:
        raise Exception(f"Credential validation failed: {str(e)}")

def create_youtube_account_from_json(credentials_file, account_name):
    """
    Main function to create a YouTube account from a JSON credentials file.
    This handles everything automatically.
    """
    try:
        # Read the credentials file
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
        
        # Process the credentials
        result = process_youtube_credentials(creds_data, account_name)
        
        return result
        
    except Exception as e:
        raise Exception(f"Failed to create YouTube account: {str(e)}")

# Example usage:
# result = create_youtube_account_from_json('path/to/credentials.json', 'My Channel')
# encrypted_creds = result['credentials']
# account_name = result['name'] 