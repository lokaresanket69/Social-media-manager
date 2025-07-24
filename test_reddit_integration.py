import json
from security import encrypt_data, decrypt_data
from reddit_api import post_to_reddit, test_reddit_connection

# Test credentials (replace with actual password)
test_credentials = {
    'client_id': 'DbmxX4UqSOEOqL0qMer7Rjg',
    'client_secret': 'o2Xv4zD_cYX4dPdCKU8zS7F4BmAhJA',
    'username': 'Leather_Emu4253',
    'password': 'Sanket@7558',  # Actual password
    'user_agent': 'script:bot2:v1.0 (by /u/Leather_Emu4253)',
    'subreddit': 'test'
}

def test_reddit_integration():
    """Test the Reddit API integration with the project's credential system."""
    
    print("=== Testing Reddit API Integration ===\n")
    
    # Test 1: Test connection
    print("1. Testing Reddit connection...")
    if test_reddit_connection(test_credentials):
        print("✅ Connection test successful!")
    else:
        print("❌ Connection test failed!")
        print("Make sure to replace '[REDDIT_PASSWORD]' with your actual password")
        return
    
    # Test 2: Test with encrypted credentials (like in the database)
    print("\n2. Testing with encrypted credentials...")
    
    # Encrypt credentials (like the app does)
    encrypted_creds = encrypt_data(json.dumps(test_credentials))
    
    # Create mock account and content objects (like the app uses)
    mock_account = {
        'credentials': encrypted_creds
    }
    
    mock_content = {
        'title': 'Test Post from Social Media Automation',
        'description': 'This is a test post from our social media automation project.',
        'hashtags': '#automation #test #socialmedia',
        'media_path': 'static/images/test.jpg'  # This won't be used for Reddit
    }
    
    try:
        result = post_to_reddit(mock_account, mock_content, '.')
        print("✅ Post successful!")
        print(f"Post URL: {result.get('url', 'N/A')}")
        print(f"Post ID: {result.get('id', 'N/A')}")
        print(f"Subreddit: {result.get('subreddit', 'N/A')}")
    except Exception as e:
        print(f"❌ Post failed: {e}")
    
    print("\n=== Integration Test Complete ===")

if __name__ == "__main__":
    test_reddit_integration() 