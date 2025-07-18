import os
import json
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from security import encrypt_data

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.readonly'
]

def process_youtube_credentials_simple(credentials_json, account_name):
    """
    Simplified YouTube credentials processing that works with both web and desktop apps
    """
    try:
        # Parse the uploaded JSON file
        if isinstance(credentials_json, str):
            creds_data = json.loads(credentials_json)
        else:
            creds_data = credentials_json
            
        # Check if it already has tokens
        if 'refresh_token' in creds_data:
            # Already has tokens, just validate
            return validate_and_return_credentials(creds_data, account_name)
        
        # For new credentials, we need to do OAuth flow
        return handle_simple_oauth_flow(creds_data, account_name)
            
    except Exception as e:
        raise Exception(f"Failed to process YouTube credentials: {str(e)}")

def handle_simple_oauth_flow(creds_data, account_name):
    """
    Simple OAuth flow that works with both web and desktop apps
    """
    try:
        # Create a temporary credentials file
        temp_creds_file = f"temp_creds_{account_name}.json"
        with open(temp_creds_file, 'w') as f:
            json.dump(creds_data, f)
        
        # Always use installed app flow (works for both web and desktop)
        flow = InstalledAppFlow.from_client_secrets_file(temp_creds_file, SCOPES)
        
        # Use a specific port to avoid conflicts
        creds = flow.run_local_server(port=8080, prompt='consent')
        
        # Clean up temp file
        os.remove(temp_creds_file)
        
        # Extract credentials info
        client_id = None
        client_secret = None
        
        if 'installed' in creds_data:
            client_id = creds_data['installed']['client_id']
            client_secret = creds_data['installed']['client_secret']
        elif 'web' in creds_data:
            client_id = creds_data['web']['client_id']
            client_secret = creds_data['web']['client_secret']
        else:
            client_id = creds_data.get('client_id')
            client_secret = creds_data.get('client_secret')
        
        # Convert to dictionary format
        creds_dict = {
            'client_id': client_id,
            'client_secret': client_secret,
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

def create_youtube_account_from_json_simple(credentials_file, account_name):
    """
    Main function to create a YouTube account from a JSON credentials file.
    This handles everything automatically.
    """
    try:
        # Read the credentials file
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
        
        # Process the credentials
        result = process_youtube_credentials_simple(creds_data, account_name)
        
        return result
        
    except Exception as e:
        raise Exception(f"Failed to create YouTube account: {str(e)}")

# Example usage:
# result = create_youtube_account_from_json_simple('path/to/credentials.json', 'My Channel')
# encrypted_creds = result['credentials']
# account_name = result['name'] 