import requests
import os
import json

def post_to_instagram(account, content):
    # Load access token
    with open(account['credential_path']) as f:
        token = f.read().strip()
    # Instagram Graph API endpoint
    url = 'https://graph.facebook.com/v17.0/me/media'
    caption = (content['description'] or '') + '\n' + (content['hashtags'] or '')
    files = {'media': open(content['media_path'], 'rb')}
    data = {
        'caption': caption,
        'access_token': token
    }
    # For images, use image_url; for videos, use video_url (here we use file upload for simplicity)
    response = requests.post(url, data=data, files=files)
    if not response.ok:
        raise Exception('Instagram API error: ' + response.text)
    return response.json() 