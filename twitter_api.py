import tweepy
import os
import json
from security import decrypt_data

def post_to_twitter(account, content, base_dir):
    """
    Posts content to Twitter, reading credentials from the account database record.
    """
    try:
        credentials = json.loads(decrypt_data(account['credentials']))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid credentials format for Twitter account.")

    consumer_key = credentials.get('consumer_key')
    consumer_secret = credentials.get('consumer_secret')
    access_token = credentials.get('access_token')
    access_token_secret = credentials.get('access_token_secret')

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise ValueError("Missing one or more required Twitter API credentials.")

    # Authenticate with Twitter API v1.1 for media uploads
    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(auth)

    # Authenticate with Twitter API v2 for tweeting
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    tweet_text = f"{content.get('title', '')}\n\n{content.get('description', '')}\n\n{content.get('hashtags', '')}".strip()
    media_path_relative = content.get('media_path')
    media_ids = []

    if media_path_relative:
        media_path_absolute = os.path.join(base_dir, media_path_relative)
        if os.path.exists(media_path_absolute):
            try:
                media = api_v1.media_upload(filename=media_path_absolute)
                media_ids.append(media.media_id_string)
            except Exception as e:
                raise Exception(f"Error uploading media to Twitter: {e}")

    try:
        if media_ids:
            response = client.create_tweet(text=tweet_text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=tweet_text)
        
        print(f"[Twitter API] Tweet posted successfully: {response.data['id']}")
        return response.data
    except Exception as e:
        raise Exception(f"Error posting tweet: {e}") 