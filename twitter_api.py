import tweepy
import os

def post_to_twitter(account, content, base_dir):
    """
    Posts content to Twitter, handling both text-only and media tweets.
    Credentials are read from environment variables based on the account ID.
    """
    account_id = account['id']
    
    # Read credentials from environment variables
    consumer_key = os.getenv(f'TWITTER_API_KEY_{account_id}')
    consumer_secret = os.getenv(f'TWITTER_API_SECRET_KEY_{account_id}')
    access_token = os.getenv(f'TWITTER_ACCESS_TOKEN_{account_id}')
    access_token_secret = os.getenv(f'TWITTER_ACCESS_TOKEN_SECRET_{account_id}')

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise Exception(f"Missing Twitter API credentials for account ID {account_id} in environment variables.")

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
                # Use API v1.1 to upload media
                media = api_v1.media_upload(filename=media_path_absolute)
                media_ids.append(media.media_id_string)
            except Exception as e:
                raise Exception(f"Error uploading media to Twitter: {e}")

    # Post the tweet using API v2
    try:
        if media_ids:
            response = client.create_tweet(text=tweet_text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=tweet_text)
        
        print(f"[Twitter API] Tweet posted successfully: {response.data['id']}")
        return response.data
    except Exception as e:
        raise Exception(f"Error posting tweet: {e}") 