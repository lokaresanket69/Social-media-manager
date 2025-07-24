import praw
import os
import json
from security import decrypt_data

def post_to_reddit(account, content, base_dir):
    """
    Posts content to Reddit using PRAW, with credentials stored in the database.
    """
    try:
        # Convert sqlite3.Row to dict if needed
        if not isinstance(content, dict):
            content = dict(content)
        
        # Decrypt and parse credentials
        creds_encrypted = account['credentials']
        creds_json = decrypt_data(creds_encrypted)
        credentials = json.loads(creds_json)
        
        # Extract credentials
        client_id = credentials.get('client_id')
        client_secret = credentials.get('client_secret')
        username = credentials.get('username')
        password = credentials.get('password')
        user_agent = credentials.get('user_agent', 'script:bot2:v1.0 (by /u/Leather_Emu4253)')
        
        if not all([client_id, client_secret, username, password]):
            raise ValueError("Missing Reddit credentials. Need client_id, client_secret, username, and password.")
        
        # Initialize Reddit instance
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        
        # Verify authentication
        try:
            reddit.user.me()
            print(f"[Reddit API] Successfully authenticated as: {reddit.user.me()}")
        except Exception as e:
            raise Exception(f"Reddit authentication failed: {e}")
        
        # Prepare post content
        title = content.get('title', 'No Title')
        description = content.get('description', '')
        hashtags = content.get('hashtags', '')
        
        # Combine description and hashtags
        post_text = f"{description}\n\n{hashtags}".strip()
        
        # Get subreddit (prefer from content, fallback to credentials, then 'test')
        subreddit_name = content.get('subreddit') or credentials.get('subreddit') or 'test'
        subreddit = reddit.subreddit(subreddit_name)

        # Validate subreddit before posting
        try:
            # Check if subreddit exists and is not banned/quarantined
            subreddit.id  # Will raise if subreddit does not exist
            # Check if user can post (try to fetch submission rules)
            rules = subreddit.rules()
            if not rules:
                raise Exception(f"Subreddit r/{subreddit_name} exists but posting rules could not be fetched.")
        except Exception as e:
            raise Exception(f"Subreddit validation failed for '{subreddit_name}': {e}")
        
        # Handle media if provided
        media_path_relative = content.get('media_path')
        if media_path_relative:
            media_path_absolute = os.path.join(base_dir, media_path_relative)
            if os.path.exists(media_path_absolute):
                # For Reddit, we'll post the image URL in the text if it's an image
                # Reddit doesn't support direct image uploads via PRAW for text posts
                post_text += f"\n\n[Image: {media_path_relative}]"
            else:
                print(f"[Reddit API] Warning: Media file not found: {media_path_absolute}")
        
        # Post to Reddit
        try:
            if post_text.strip():
                # Text post
                submission = subreddit.submit(
                    title=title,
                    selftext=post_text
                )
            else:
                # Link post (just title)
                submission = subreddit.submit(
                    title=title,
                    url="https://www.reddit.com"
                )
            
            print(f"[Reddit API] Post successful! URL: {submission.url}")
            return {
                'success': True,
                'url': submission.url,
                'id': submission.id,
                'subreddit': subreddit_name
            }
            
        except Exception as e:
            raise Exception(f"Failed to post to Reddit: {e}")
            
    except Exception as e:
        print(f"[Reddit API] Error: {e}")
        raise Exception(f"Reddit API Error: {e}")

def test_reddit_connection(credentials):
    """
    Test function to verify Reddit credentials work.
    """
    try:
        reddit = praw.Reddit(
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            username=credentials['username'],
            password=credentials['password'],
            user_agent=credentials.get('user_agent', 'script:bot2:v1.0 (by /u/Leather_Emu4253)')
        )
        
        # Test authentication
        user = reddit.user.me()
        print(f"[Reddit Test] Successfully authenticated as: {user}")
        
        # Test subreddit access
        subreddit_name = credentials.get('subreddit', 'test')
        subreddit = reddit.subreddit(subreddit_name)
        print(f"[Reddit Test] Successfully accessed subreddit: r/{subreddit_name}")
        
        return True
        
    except Exception as e:
        print(f"[Reddit Test] Error: {e}")
        return False 