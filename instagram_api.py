from instagrapi import Client
import os
import mimetypes

def post_to_instagram(account, content, base_dir):
    """
    Posts content to Instagram, handling both photo and video uploads.
    Authenticates using username and password from environment variables.
    """
    account_id = account['id']
    
    # Read credentials from environment variables
    username = os.getenv(f'INSTAGRAM_USERNAME_{account_id}')
    password = os.getenv(f'INSTAGRAM_PASSWORD_{account_id}')

    if not all([username, password]):
        raise Exception(f"Missing Instagram credentials for account ID {account_id} in environment variables.")

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

    # Determine media type and upload
    media_type = mimetypes.guess_type(media_path_absolute)[0]
    
    try:
        if media_type and media_type.startswith('image/'):
            print(f"[Instagram API] Uploading photo: {media_path_absolute}")
            response = cl.photo_upload(path=media_path_absolute, caption=caption)
        elif media_type and media_type.startswith('video/'):
            print(f"[Instagram API] Uploading video: {media_path_absolute}")
            response = cl.video_upload(path=media_path_absolute, caption=caption)
        else:
            raise Exception(f"Unsupported media type for Instagram: {media_type}")
        
        print(f"[Instagram API] Post successful: {response.pk}")
        return response.dict()
    except Exception as e:
        raise Exception(f"Error posting to Instagram: {e}")
    finally:
        cl.logout() 