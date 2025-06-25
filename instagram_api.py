from instagrapi import Client
import os
import mimetypes
import json

def post_to_instagram(account, content, base_dir):
    """
    Posts content to Instagram, using credentials stored in the database.
    """
    try:
        credentials = json.loads(account['credentials'])
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid credentials format for Instagram account.")

    username = credentials.get('username')
    password = credentials.get('password')

    if not all([username, password]):
        raise ValueError("Missing Instagram username or password.")

    # Authenticate
    cl = Client()
    try:
        cl.login(username, password)
    except Exception as e:
        raise Exception(f"Instagram login failed for account {username}: {e}")

    caption = f"{content.get('title', '')}\n\n{content.get('description', '')}\n\n{content.get('hashtags', '')}".strip()
    media_path_relative = content.get('media_path')
    
    if not media_path_relative:
        raise Exception("No media path provided for Instagram post.")

    media_path_absolute = os.path.join(base_dir, media_path_relative)
    if not os.path.exists(media_path_absolute):
        raise Exception(f"Media file not found at: {media_path_absolute}")

    media_type = mimetypes.guess_type(media_path_absolute)[0]
    
    try:
        if media_type and media_type.startswith('image/'):
            response = cl.photo_upload(path=media_path_absolute, caption=caption)
        elif media_type and media_type.startswith('video/'):
            response = cl.video_upload(path=media_path_absolute, caption=caption)
        else:
            raise Exception(f"Unsupported media type for Instagram: {media_type}")
        
        print(f"[Instagram API] Post successful: {response.pk}")
        return response.dict()
    except Exception as e:
        raise Exception(f"Error posting to Instagram: {e}")
    finally:
        cl.logout() 