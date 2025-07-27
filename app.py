from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone
import json
from dateutil.parser import isoparse
from dateutil.tz import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler
from security import encrypt_data, decrypt_data
import requests
from urllib.parse import urlencode

# --- Local API Modules ---
from scheduler import process_scheduled_posts
from youtube_api import post_to_youtube
from instagram_api import post_to_instagram  # Enable Instagram
from twitter_api import post_to_twitter
from pinterest_api import post_to_pinterest

from linkedin_api import post_to_linkedin
from reddit_api import post_to_reddit
from youtube_auth_simple import get_youtube_auth_url, exchange_code_and_store_credentials
from youtube_auth import process_youtube_credentials  # Import the correct function

# --- App Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
CORS(app)
DB_PATH = os.path.join(BASE_DIR, 'social_media_automation.db')

# --- Database Functions ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS platforms (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, platform_id INTEGER NOT NULL, name TEXT NOT NULL,
        credentials TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(platform_id) REFERENCES platforms(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, title TEXT NOT NULL,
        description TEXT, hashtags TEXT, media_path TEXT NOT NULL, schedule_time TEXT,
        status TEXT DEFAULT 'pending', error TEXT, created_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )''')
    platforms = [
        ('youtube', 'YouTube'), ('instagram', 'Instagram'), ('twitter', 'Twitter'),
        ('pinterest', 'Pinterest'), ('linkedin', 'LinkedIn'),
        ('reddit', 'Reddit')
    ]
    c.executemany('INSERT OR IGNORE INTO platforms (name, display_name) VALUES (?, ?)', platforms)
    conn.commit()
    conn.close()

init_db()

# --- API Endpoints ---
@app.route('/api/platforms')
def api_platforms():
    conn = get_db()
    platforms = conn.execute('SELECT * FROM platforms').fetchall()
    conn.close()
    return jsonify([dict(row) for row in platforms])

@app.route('/api/accounts', methods=['GET', 'POST'])
def api_accounts():
    import json  # Ensure json is always available
    from youtube_auth import process_youtube_credentials  # Import the correct function
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        platform_id = data.get('platform_id')
        name = data.get('account_name')
        credentials = {}
        # Check platform early
        platform_name = None
        if platform_id:
            c = conn.cursor()
            platform = c.execute('SELECT name FROM platforms WHERE id=?', (platform_id,)).fetchone()
            if platform:
                platform_name = platform['name']
        # Instagram: use username/password fields only
        if platform_name == 'instagram':
            username = data.get('username')
            password = data.get('password')
            if username and password:
                credentials = {"username": username, "password": password}
            else:
                return jsonify({'error': 'Instagram username and password are required.'}), 400
        elif platform_name == 'youtube':
            # Adding YouTube accounts must be done via the web-based OAuth flow.
            return jsonify({'error': 'To add a YouTube account, please use the web-based OAuth flow via /youtube/authorize.'}), 400
        else:
            # Handle uploaded credential file
            if 'credential' in request.files and request.files['credential'].filename:
                cred_file = request.files['credential']
                try:
                    raw_creds = json.load(cred_file)
                    # Accept both flat and nested (installed/web) formats
                    if 'client_id' in raw_creds and 'client_secret' in raw_creds:
                        credentials = raw_creds
                    elif 'installed' in raw_creds:
                        credentials = raw_creds['installed']
                    elif 'web' in raw_creds:
                        credentials = raw_creds['web']
                    else:
                        return jsonify({'error': 'Unrecognized credential file format. Please upload a valid Google OAuth credentials file.'}), 400
                except Exception as e:
                    return jsonify({'error': f'Failed to parse credential file: {e}'}), 400
            elif 'credential_token' in data and data['credential_token']:
                try:
                    credentials = json.loads(data['credential_token'])
                except Exception as e:
                    return jsonify({'error': f'Failed to parse credential token: {e}'}), 400
            # Fallback: use any other form fields as credentials
            if not credentials:
                credentials = {key: value for key, value in data.items() if key not in ['platform_id', 'account_name']}
        if not all([platform_id, name, credentials]):
            return jsonify({'error': 'Platform, Account Name, and Credentials are required.'}), 400
        # Special handling for YouTube: process credentials automatically
        if platform_id:
            c = conn.cursor()
            platform = c.execute('SELECT name FROM platforms WHERE id=?', (platform_id,)).fetchone()
            if platform and platform['name'] == 'youtube':
                # Instruct user to use the new OAuth flow
                return jsonify({'error': 'YouTube account connection now requires the new OAuth flow. Please use /youtube/authorize to connect your YouTube account.'}), 400
        # Special handling for Reddit: process and validate credentials from form fields
        if platform_id:
            c = conn.cursor()
            platform = c.execute('SELECT name FROM platforms WHERE id=?', (platform_id,)).fetchone()
            if platform and platform['name'] == 'reddit':
                # Accept credentials as dict or string
                import json
                if isinstance(credentials, str):
                    try:
                        credentials = json.loads(credentials)
                    except Exception:
                        # If not JSON, treat as form fields
                        credentials = {key: value for key, value in data.items() if key not in ['platform_id', 'account_name']}
                # Required fields
                required = ['client_id', 'client_secret', 'username', 'password']
                missing = [k for k in required if not credentials.get(k)]
                if missing:
                    return jsonify({'error': f'Missing Reddit credentials: {", ".join(missing)}'}), 400
                # Set default user_agent if not provided
                if not credentials.get('user_agent'):
                    credentials['user_agent'] = f'script:{credentials["username"]}:v1.0 (by /u/{credentials["username"]})'
                # Set default subreddit if not provided
                if not credentials.get('subreddit'):
                    credentials['subreddit'] = 'test'
                # Test credentials before saving
                try:
                    from reddit_api import test_reddit_connection
                    if not test_reddit_connection(credentials):
                        return jsonify({'error': 'Reddit authentication failed: Invalid credentials or subreddit access.'}), 400
                except Exception as e:
                    return jsonify({'error': f'Reddit authentication failed: {str(e)}'}), 400
        # Special handling for Twitter: process and validate credentials from form fields
        if platform_id:
            c = conn.cursor()
            platform = c.execute('SELECT name FROM platforms WHERE id=?', (platform_id,)).fetchone()
            if platform and platform['name'] == 'twitter':
                import json
                if isinstance(credentials, str):
                    try:
                        credentials = json.loads(credentials)
                    except Exception:
                        credentials = {key: value for key, value in data.items() if key not in ['platform_id', 'account_name']}
                # Only accept api_key, api_key_secret, access_token, access_token_secret
                required = ['api_key', 'api_key_secret', 'access_token', 'access_token_secret']
                missing = [k for k in required if not credentials.get(k)]
                if missing:
                    return jsonify({'error': f'Missing Twitter credentials: {", ".join(missing)}. Please provide all four keys as shown in the form.'}), 400
                # Test credentials before saving
                try:
                    from twitter_api import test_twitter_connection
                    if not test_twitter_connection(credentials):
                        return jsonify({'error': 'Twitter authentication failed: Invalid credentials or permissions. Please double-check your keys and try again.'}), 400
                except Exception as e:
                    return jsonify({'error': f'Twitter authentication failed: {str(e)}'}), 400
        # Credential validation logic
        try:
            # Map platform_id to platform name
            c = conn.cursor()
            platform = c.execute('SELECT name FROM platforms WHERE id=?', (platform_id,)).fetchone()
            if not platform:
                return jsonify({'error': 'Invalid platform selected.'}), 400
            platform_name = platform['name']
            # Define dummy_content for validation
            dummy_content = {
                "title": "Test",
                "description": "Test",
                "hashtags": "",
                "media_path": "static/images/test.jpg"
            }
            # Try to validate credentials using the API function
            api_func = platform_apis.get(platform_name)
            if api_func:
                # Dummy content for validation (minimal, won't post)
                if platform_name == 'youtube':
                    # YouTube credentials are already validated in the processing step above
                    pass  # Skip validation since we already processed and validated
                elif platform_name == 'twitter':
                    # For Twitter, only test credentials, do not require media file
                    try:
                        from twitter_api import test_twitter_connection
                        if not test_twitter_connection(credentials):
                            return jsonify({'error': 'Credential validation failed: Twitter credentials are invalid. Please check your keys and try again.'}), 400
                    except Exception as e:
                        return jsonify({'error': f'Credential validation failed: {str(e)}'}), 400
                else:
                    try:
                        api_func({'credentials': encrypt_data(json.dumps(credentials))}, dummy_content, BASE_DIR)
                    except ValueError as e:
                        if platform_name == 'instagram' and 'Invalid credentials format' in str(e):
                            return jsonify({'error': 'Credential validation failed: Instagram credentials must be a JSON object with "username" and "password" fields, e.g. {"username": "your_instagram_username", "password": "your_instagram_password"}.'}), 400
                        return jsonify({'error': f'Credential validation failed: {str(e)}'}), 400
                    except Exception as e:
                        return jsonify({'error': f'Credential validation failed: {str(e)}'}), 400
            encrypted_credentials = encrypt_data(json.dumps(credentials))
            c.execute('INSERT INTO accounts (platform_id, name, credentials, created_at) VALUES (?, ?, ?, ?)',
                      (platform_id, name, encrypted_credentials, datetime.utcnow().isoformat()))
            conn.commit()
            flash(f"Account '{name}' created successfully.", "success")
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': f'Failed to create account: {e}'}), 500
        finally:
            conn.close()
    else:
        platform_id = request.args.get('platform_id')
        query = 'SELECT id, platform_id, name, created_at FROM accounts'
        params = []
        if platform_id:
            query += ' WHERE platform_id=?'
            params.append(platform_id)
        accounts = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(row) for row in accounts])

@app.route('/api/content', methods=['GET', 'POST'])
def api_content():
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        account_id = data.get('account_id')
        title = data.get('title')
        description = data.get('description')
        hashtags = data.get('hashtags')
        schedule_time_str = data.get('schedule_time')
        created_at = datetime.utcnow().isoformat()
        
        # Process schedule_time: convert local time from form to UTC
        schedule_time_utc_iso = None
        if schedule_time_str:
            try:
                # Parse schedule_time string
                dt = isoparse(schedule_time_str)
                # If timezone info is missing, assume browser local tz (server may be UTC)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tzlocal())
                utc_time = dt.astimezone(timezone.utc)
                schedule_time_utc_iso = utc_time.isoformat()
            except ValueError as e:
                print(f"Error parsing schedule time '{schedule_time_str}': {e}")
                return jsonify({'error': f'Invalid schedule time format: {schedule_time_str}'}), 400

        # Verify account exists
        account = conn.execute('SELECT * FROM accounts WHERE id=?', 
                             (account_id,)).fetchone()
        if not account:
            return jsonify({'error': 'Invalid account'}), 400
            
        # Save media file (optional)
        media_path = None
        if 'media' in request.files and request.files['media'] and request.files['media'].filename:
            file = request.files['media']
            uploads_dir = os.path.join(BASE_DIR, 'uploads')
            # Always ensure uploads directory exists (robust and reliable)
            try:
                os.makedirs(uploads_dir, exist_ok=True)
            except Exception as e:
                return jsonify({'error': f'Failed to create uploads directory: {str(e)}'}), 500
            media_path = os.path.join('uploads', f"{file.filename}")
            try:
                file.save(os.path.join(BASE_DIR, media_path))
            except Exception as e:
                return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        # If no media, media_path remains None
            
        try:
            c = conn.cursor()
            c.execute('''INSERT INTO content (account_id, title, description, hashtags, 
                         media_path, schedule_time, created_at) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (account_id, title, description, hashtags, 
                       media_path if media_path else '', schedule_time_utc_iso, created_at))
            conn.commit()
            conn.close()
            flash('Content scheduled successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            return jsonify({'error': f'Failed to save content: {str(e)}'}), 500
    else:
        account_id = request.args.get('account_id')
        if account_id:
            rows = conn.execute('''SELECT * FROM content 
                                 WHERE account_id=?''', 
                              (account_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM content').fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])

@app.route('/api/errors', methods=['GET'])
def api_errors():
    conn = get_db()
    errors = conn.execute('SELECT * FROM content WHERE status="error"').fetchall()
    conn.close()
    return jsonify([dict(row) for row in errors])

# --- Page Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    conn = get_db()
    platforms = conn.execute('SELECT * FROM platforms').fetchall()
    accounts = conn.execute('SELECT * FROM accounts').fetchall()
    content = conn.execute('SELECT * FROM content').fetchall()
    conn.close()
    return render_template('dashboard.html', 
                         platforms=platforms,
                         accounts=accounts,
                         content_items=content)

@app.route('/platform/<platform_name>')
def platform_page(platform_name):
    conn = get_db()
    platform = conn.execute('SELECT * FROM platforms WHERE name=?', 
                          (platform_name,)).fetchone()
    accounts = conn.execute('''SELECT * FROM accounts 
                             WHERE platform_id=?''', 
                          (platform['id'],)).fetchall() if platform else []
    content = []
    if accounts:
        account_ids = tuple([a['id'] for a in accounts])
        if len(account_ids) == 1:
            content = conn.execute('''SELECT * FROM content 
                                    WHERE account_id=?''', 
                                 (account_ids[0],)).fetchall()
        elif len(account_ids) > 1:
            q = f'''SELECT * FROM content 
                   WHERE account_id IN ({','.join(['?']*len(account_ids))})'''
            content = conn.execute(q, account_ids).fetchall()
    conn.close()
    return render_template('platform.html', 
                         platform=platform,
                         accounts=accounts,
                         content_items=content)

# The old YouTube OAuth routes (authorize_youtube, oauth2callback_youtube) are no longer needed
# as credentials are now added directly in the 'Add Account' form. They have been removed.

import os
from flask import redirect, request
import requests
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")  # Use .env value, not hardcoded

# Store tokens and person URNs in memory for demo (replace with DB in production)
linkedin_person_urns = {}
linkedin_post_tokens = {}

@app.route("/linkedin/auth")
def linkedin_auth_redirect():
    """
    Redirect /linkedin/auth to the correct OIDC endpoint for backward compatibility.
    """
    return redirect(url_for('linkedin_auth_oidc'))

@app.route("/linkedin/auth-oidc")
def linkedin_auth_oidc():
    scope = "openid profile email"
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}/oidc"
        f"&scope={scope.replace(' ', '%20')}"
    )
    return f'<a href="{auth_url}"><button>Connect LinkedIn (Get Person URN)</button></a>'

@app.route("/linkedin/callback/oidc")
def linkedin_callback_oidc():
    code = request.args.get("code")
    error = request.args.get("error")
    error_description = request.args.get("error_description")
    if error:
        return f"LinkedIn OIDC error: {error} - {error_description if error_description else ''}", 400
    if not code:
        return f"No code provided in callback. Full query: {request.query_string.decode()}", 400
    # Exchange code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{LINKEDIN_REDIRECT_URI}/oidc",
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    try:
        resp = requests.post(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if resp.status_code != 200:
            return f"Failed to get OIDC access token: {resp.text}", 400
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return f"No access token in response: {token_data}", 400
        # Fetch user info from /userinfo endpoint
        userinfo_resp = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code != 200:
            return f"Failed to fetch LinkedIn userinfo: {userinfo_resp.text}", 400
        userinfo = userinfo_resp.json()
        person_urn = f"urn:li:person:{userinfo['sub']}"
        email = userinfo.get('email')
        name = userinfo.get('name', email)
        # Store info in session for registration
        session['linkedin_account'] = {
            'access_token': access_token,
            'person_urn': person_urn,
            'email': email,
            'name': name
        }
        # Redirect to registration endpoint
        return redirect(url_for('linkedin_register_account'))
    except Exception as e:
        return f"LinkedIn callback processing failed: {str(e)}", 500

@app.route("/linkedin/register-account")
def linkedin_register_account():
    account = session.pop('linkedin_account', None)
    if not account:
        return "No LinkedIn account info found in session. Please connect again.", 400
    conn = get_db()
    c = conn.cursor()
    # Get LinkedIn platform_id
    platform = c.execute('SELECT id FROM platforms WHERE name=?', ('linkedin',)).fetchone()
    if not platform:
        conn.close()
        return "LinkedIn platform not found in DB.", 500
    platform_id = platform['id']
    # Check if account already exists
    existing = c.execute('SELECT id FROM accounts WHERE platform_id=? AND name=?', (platform_id, account['name'])).fetchone()
    if existing:
        conn.close()
        flash('LinkedIn account already registered.', 'info')
        return redirect(url_for('platform_page', platform_name='linkedin'))
    # Store credentials as JSON
    credentials = {
        'access_token': account['access_token'],
        'person_urn': account['person_urn'],
        'email': account['email']
    }
    encrypted_credentials = encrypt_data(json.dumps(credentials))
    
    # Insert the account
    c.execute('INSERT INTO accounts (platform_id, name, credentials, created_at) VALUES (?, ?, ?, ?)',
              (platform_id, account['name'], encrypted_credentials, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    flash('LinkedIn account registered successfully!', 'success')
    return redirect(url_for('platform_page', platform_name='linkedin'))
@app.route("/linkedin/auth-post")
def linkedin_auth_post():
    email = request.args.get("email")
    if not email:
        return "Missing email. Please authenticate with OIDC first.", 400
    scope = "r_liteprofile w_member_social"
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}/post"
        f"&scope={scope.replace(' ', '%20')}"
        f"&state={email}"
    )
    return f'<a href="{auth_url}"><button>Connect LinkedIn for Posting</button></a>'

@app.route("/linkedin/callback/post")
def linkedin_callback_post():
    code = request.args.get("code")
    error = request.args.get("error")
    error_description = request.args.get("error_description")
    email = request.args.get("state")
    if error:
        return f"LinkedIn OAuth error: {error} - {error_description if error_description else ''}", 400
    if not code or not email:
        return f"No code or email provided in callback. Full query: {request.query_string.decode()}", 400
    # Exchange code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{LINKEDIN_REDIRECT_URI}/post",
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    resp = requests.post(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if resp.status_code != 200:
        return f"Failed to get posting access token: {resp.text}", 400
    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return f"No access token in response: {token_data}", 400
    # Store posting access token in memory (replace with DB in production)
    linkedin_post_tokens[email] = access_token
    return f"LinkedIn posting authentication successful!<br>Access Token stored for posting.<br><a href='/linkedin/post-example?email={email}'>Post Example</a>"


@app.route("/linkedin/post-example")
def linkedin_post_example():
    email = request.args.get("email")
    person_urn = linkedin_person_urns.get(email)
    access_token = linkedin_post_tokens.get(email)
    if not person_urn or not access_token:
        return "No Person URN or access token found for this user. Please authenticate with both OIDC and posting flows.", 400
    # Prepare post body as per LinkedIn docs
    post_body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": "Hello World! This is my first Share on LinkedIn!"},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    resp = requests.post("https://api.linkedin.com/v2/ugcPosts", json=post_body, headers=headers)
    if resp.status_code == 201:
        return f"Post successful! LinkedIn response: {resp.json()}"
    else:
        return f"Failed to post: {resp.status_code} {resp.text}", 400

# --- YouTube OAuth Web Flow ---
from youtube_auth_simple import get_youtube_auth_url, exchange_code_and_store_credentials

@app.route('/youtube/authorize')
def youtube_authorize():
    """
    Redirect user to Google's OAuth 2.0 server for YouTube authentication.
    Optionally, pass ?account_name=... as a query param.
    """
    account_name = request.args.get('account_name', 'YouTube User')
    # Store account_name in session for use after callback
    session['pending_youtube_account_name'] = account_name
    auth_url = get_youtube_auth_url()
    return redirect(auth_url)

@app.route('/youtube/oauth2callback')
def youtube_oauth2callback():
    """
    Handle Google's redirect, exchange code for tokens, validate, and store credentials.
    """
    error = request.args.get('error')
    if error:
        flash(f"YouTube OAuth error: {error}", "danger")
        return redirect(url_for('platform_page', platform_name='youtube'))
    code = request.args.get('code')
    if not code:
        flash("Missing code in callback.", "danger")
        return redirect(url_for('platform_page', platform_name='youtube'))
    account_name = session.pop('pending_youtube_account_name', 'YouTube User')
    try:
        result = exchange_code_and_store_credentials(code, account_name)
        # Save the new YouTube account to the database if not already present
        conn = get_db()
        c = conn.cursor()
        platform = c.execute('SELECT id FROM platforms WHERE name=?', ('youtube',)).fetchone()
        if platform:
            platform_id = platform['id']
            encrypted_credentials = result['credentials']
            # Avoid duplicate accounts by channel_id
            existing = c.execute('SELECT id FROM accounts WHERE platform_id=? AND name=?', (platform_id, result['name'])).fetchone()
            if not existing:
                c.execute('INSERT INTO accounts (platform_id, name, credentials, created_at) VALUES (?, ?, ?, ?)',
                          (platform_id, result['name'], encrypted_credentials, datetime.utcnow().isoformat()))
                conn.commit()
        conn.close()
        flash(f"YouTube channel '{result['channel_info']['name']}' added successfully!", "success")
        return redirect(url_for('platform_page', platform_name='youtube'))
    except Exception as e:
        flash(f"YouTube authentication failed: {str(e)}", "danger")
        return redirect(url_for('platform_page', platform_name='youtube'))

@app.route('/delete/account/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    conn = get_db()
    c = conn.cursor()
    try:
        # Optionally check for _method=DELETE, but not strictly necessary for this simple case
        # method = request.form.get('_method', '').upper()
        # if method != 'DELETE':
        #     return jsonify({'error': 'Method not allowed'}), 405
            
        c.execute('DELETE FROM accounts WHERE id=?', (account_id,))
        deleted_rows = c.rowcount
        conn.commit()
        conn.close()

        if deleted_rows == 0:
            return jsonify({'error': 'Account not found'}), 404

        # Also delete associated content
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM content WHERE account_id=?', (account_id,))
        conn.commit()
        conn.close()

        # Optionally delete credential file associated with the account
        # This would require retrieving the credential_path before deleting the account
        # and handling temporary files carefully.
        # For simplicity, this is omitted for now.

        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error deleting account {account_id}: {e}")
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500

@app.route('/delete/content/<int:content_id>', methods=['POST'])
def delete_content(content_id):
    conn = get_db()
    conn.execute('DELETE FROM content WHERE id = ?', (content_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# --- Scheduler Setup ---
platform_apis = {
    'youtube': post_to_youtube,
    'instagram': post_to_instagram,  # Enabled
    'twitter': post_to_twitter,
    'pinterest': post_to_pinterest,

    'linkedin': post_to_linkedin,
    'reddit': post_to_reddit,
}

scheduler = BackgroundScheduler(timezone=timezone.utc)
scheduler.add_job(
    func=process_scheduled_posts,
    trigger='interval',
    minutes=1,
    args=[get_db, platform_apis, BASE_DIR]
)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True) 