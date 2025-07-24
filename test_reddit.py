import praw
import json

# Reddit credentials
credentials = {
    'client_id': 'DbmxX4UqSOEOqL0qMer7Rjg',
    'client_secret': 'o2Xv4zD_cYX4dPdCKU8zS7F4BmAhJA',
    'username': 'Leather_Emu4253',
    'password': 'Sanket@7558',  # Actual password
    'user_agent': 'script:bot2:v1.0 (by /u/Leather_Emu4253)',
    'subreddit': 'test'
}

def test_reddit_connection():
    """Test Reddit API connection and post a test message."""
    try:
        # Initialize Reddit instance
        reddit = praw.Reddit(
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            username=credentials['username'],
            password=credentials['password'],
            user_agent=credentials['user_agent']
        )
        
        # Test authentication
        user = reddit.user.me()
        print(f"[Reddit Test] Successfully authenticated as: {user}")
        
        # Test subreddit access
        subreddit_name = credentials['subreddit']
        subreddit = reddit.subreddit(subreddit_name)
        print(f"[Reddit Test] Successfully accessed subreddit: r/{subreddit_name}")
        
        # Post a test message
        title = "Test Post from Social Media Automation Bot"
        text = "This is a test post from our social media automation project.\n\n#automation #test #socialmedia"
        
        submission = subreddit.submit(
            title=title,
            selftext=text
        )
        
        print(f"[Reddit Test] Post successful!")
        print(f"[Reddit Test] Post URL: {submission.url}")
        print(f"[Reddit Test] Post ID: {submission.id}")
        
        return {
            'success': True,
            'url': submission.url,
            'id': submission.id
        }
        
    except Exception as e:
        print(f"[Reddit Test] Error: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    print("Testing Reddit API connection...")
    result = test_reddit_connection()
    
    if result['success']:
        print("\n✅ Reddit API test successful!")
        print(f"Post URL: {result['url']}")
    else:
        print(f"\n❌ Reddit API test failed: {result['error']}\n")
        print("Make sure to:")
        print("1. Replace '[REDDIT_PASSWORD]' with your actual Reddit password")
        print("2. Verify your Reddit app credentials are correct")
        print("3. Ensure your Reddit account has permission to post to r/test") 