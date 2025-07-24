import sqlite3
import json
from security import encrypt_data
from datetime import datetime

# Reddit credentials (replace password with actual password)
reddit_credentials = {
    'client_id': 'DbmxX4UqSOEOqL0qMer7Rjg',
    'client_secret': 'o2Xv4zD_cYX4dPdCKU8zS7F4BmAhJA',
    'username': 'Leather_Emu4253',
    'password': 'Sanket@7558',  # Actual password
    'user_agent': 'script:bot2:v1.0 (by /u/Leather_Emu4253)',
    'subreddit': 'test'
}

def add_reddit_account():
    """Add Reddit account to the database for testing."""
    
    # Connect to database
    conn = sqlite3.connect('social_media_automation.db')
    conn.row_factory = sqlite3.Row
    
    try:
        # Get Reddit platform ID
        platform = conn.execute('SELECT id FROM platforms WHERE name = ?', ('reddit',)).fetchone()
        if not platform:
            print("❌ Reddit platform not found in database. Make sure to run the app first to initialize the database.")
            return
        
        platform_id = platform['id']
        
        # Encrypt credentials
        encrypted_credentials = encrypt_data(json.dumps(reddit_credentials))
        
        # Add account
        conn.execute('''INSERT INTO accounts (platform_id, name, credentials, created_at) 
                       VALUES (?, ?, ?, ?)''',
                    (platform_id, 'Reddit Test Account', encrypted_credentials, datetime.utcnow().isoformat()))
        
        conn.commit()
        print("✅ Reddit account added successfully!")
        print("Account name: Reddit Test Account")
        print("Platform: Reddit")
        print("Subreddit: test")
        print("\nYou can now use this account in the web interface.")
        
    except Exception as e:
        print(f"❌ Error adding Reddit account: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Adding Reddit account to database...")
    print("Make sure to replace '[REDDIT_PASSWORD]' with your actual Reddit password in the script.")
    add_reddit_account() 