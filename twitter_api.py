import tweepy
import os
import json
from security import decrypt_data
import logging

def post_to_twitter(account, content, base_dir):
    """
    Posts content to Twitter, reading credentials from the account database record.
    Now uses robust error handling and consistent key usage.
    """
    try:
        credentials = json.loads(decrypt_data(account['credentials']))
    except (json.JSONDecodeError, TypeError):
        logging.error("[Twitter] Invalid credentials format for Twitter account.")
        raise ValueError("Invalid credentials format for Twitter account. Please re-add the account with correct keys.")

    api_key = credentials.get('api_key')
    api_key_secret = credentials.get('api_key_secret')
    access_token = credentials.get('access_token')
    access_token_secret = credentials.get('access_token_secret')

    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        logging.error("[Twitter] Missing one or more required Twitter API credentials.")
        raise ValueError("Missing one or more required Twitter API credentials. Please check your keys and try again.")

    # Authenticate with Twitter API v1.1 for media uploads
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_key_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
    except Exception as e:
        logging.error(f"[Twitter] Authentication failed: {e}")
        raise Exception("Twitter authentication failed. Please check your credentials.")

    # Authenticate with Twitter API v2 for tweeting
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
    except Exception as e:
        logging.error(f"[Twitter] Client initialization failed: {e}")
        raise Exception("Twitter client initialization failed. Please check your credentials.")

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
                logging.error(f"[Twitter] Error uploading media: {e}")
                raise Exception("Error uploading media to Twitter. Please ensure the file is a supported image or video format.")
        else:
            logging.error(f"[Twitter] Media file not found: {media_path_absolute}")
            raise Exception("Media file not found. Please re-upload your file.")

    try:
        if media_ids:
            response = client.create_tweet(text=tweet_text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=tweet_text)
        logging.info(f"[Twitter] Tweet posted successfully: {response.data['id']}")
        return True
    except Exception as e:
        logging.error(f"[Twitter] Error posting tweet: {e}")
        raise Exception("Error posting tweet. Please try again later or check your content for issues.")

def test_twitter_connection(credentials):
    """
    Test function to verify Twitter credentials work. Uses robust error handling and consistent key usage.
    """
    try:
        api_key = credentials.get('api_key')
        api_key_secret = credentials.get('api_key_secret')
        access_token = credentials.get('access_token')
        access_token_secret = credentials.get('access_token_secret')
        if not all([api_key, api_key_secret, access_token, access_token_secret]):
            return False
        auth = tweepy.OAuth1UserHandler(api_key, api_key_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
        user = api.verify_credentials()
        if user:
            logging.info(f"[Twitter Test] Successfully authenticated as: {user.screen_name}")
            return True
        else:
            logging.error("[Twitter Test] Authentication failed.")
            return False
    except Exception as e:
        logging.error(f"[Twitter Test] Error: {e}")
        return False 