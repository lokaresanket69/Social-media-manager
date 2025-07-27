import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from security import encrypt_data

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.readonly'
]

# Path to your Google OAuth client secrets file (web application type)
CLIENT_SECRETS_FILE = os.getenv('GOOGLE_CLIENT_SECRETS', 'client_secret.json')
REDIRECT_URI = os.getenv('YOUTUBE_REDIRECT_URI', 'https://social-media-manager-5j5s.onrender.com/youtube/oauth2callback')

# 1. Generate the Google OAuth URL for user consent
def get_youtube_auth_url(state=None):
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return auth_url
    except FileNotFoundError:
        raise Exception(f"Google OAuth client secrets file not found at '{CLIENT_SECRETS_FILE}'. Please upload it to your server and set the GOOGLE_CLIENT_SECRETS environment variable if needed.")

# 2. Exchange the authorization code for tokens and validate
def exchange_code_and_store_credentials(code, account_name):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    creds_dict = {
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'token': creds.token
    }
    # Validate and enrich credentials
    return validate_and_return_credentials(creds_dict, account_name)

# 3. Validate credentials and return encrypted result
def validate_and_return_credentials(creds_dict, account_name):
    try:
        creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
        youtube = build('youtube', 'v3', credentials=creds)
        channels_response = youtube.channels().list(mine=True, part='snippet').execute()
        if not channels_response.get('items'):
            raise Exception("No YouTube channels found for this account")
        channel = channels_response['items'][0]
        channel_name = channel['snippet']['title']
        creds_dict['channel_name'] = channel_name
        creds_dict['channel_id'] = channel['id']
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