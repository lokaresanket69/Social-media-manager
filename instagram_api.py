import os
import requests
import json
from security import decrypt_data

def post_to_instagram(account, content, base_dir):
    """
    Posts content to Instagram using the Instagram Graph API with an access token.
    Requires:
      - access_token: Instagram Graph API token (from Meta Developers)
      - ig_user_id: Instagram Business Account ID
    """
    # Convert sqlite3.Row to dict if needed
    if not isinstance(content, dict):
        content = dict(content)
    try:
        creds_encrypted = account['credentials']
        creds_json = decrypt_data(creds_encrypted)
        credentials = json.loads(creds_json)
    except (json.JSONDecodeError, TypeError, KeyError):
        raise ValueError("Invalid credentials format for Instagram account.")

    access_token = credentials.get('access_token')
    ig_user_id = credentials.get('ig_user_id')
    if not access_token or not ig_user_id:
        raise ValueError("Missing Instagram access_token or ig_user_id in credentials.")

    # Prepare media
    caption = f"{content.get('title', '')}\n\n{content.get('description', '')}\n\n{content.get('hashtags', '')}".strip()
    media_path_relative = content.get('media_path')
    if not media_path_relative:
        raise Exception("No media path provided for Instagram post.")
    media_path_absolute = os.path.join(base_dir, media_path_relative)
    if not os.path.exists(media_path_absolute):
        raise Exception(f"Media file not found at: {media_path_absolute}")

    # Step 1: Upload the image to a publicly accessible location (Instagram Graph API requires a public URL)
    # For demo purposes, this script assumes you already have a public URL for the image.
    # In production, you should upload the image to a service like AWS S3, Imgur, or your own server.
    # Here, we'll raise an error if the image is not a URL.
    if media_path_absolute.startswith('http://') or media_path_absolute.startswith('https://'):
        image_url = media_path_absolute
    else:
        raise Exception("Instagram Graph API requires a public image URL. Please upload your image to a public location and provide the URL as media_path.")

    # Step 2: Create a media object (container)
    create_media_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': access_token
    }
    resp = requests.post(create_media_url, data=payload)
    if resp.status_code != 200:
        raise Exception(f"Failed to create Instagram media container: {resp.text}")
    media_id = resp.json().get('id')
    if not media_id:
        raise Exception(f"No media ID returned from Instagram: {resp.text}")

    # Step 3: Publish the media object
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    publish_payload = {
        'creation_id': media_id,
        'access_token': access_token
    }
    publish_resp = requests.post(publish_url, data=publish_payload)
    if publish_resp.status_code != 200:
        raise Exception(f"Failed to publish Instagram media: {publish_resp.text}")
    result = publish_resp.json()
    print(f"[Instagram Graph API] Post successful: {result}")
    return result 