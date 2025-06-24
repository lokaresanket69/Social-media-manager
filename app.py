from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import json
from dateutil.parser import isoparse
from dateutil.tz import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler

# --- Local API Modules ---
from scheduler import process_scheduled_posts
from youtube_api import post_to_youtube
from instagram_api import post_to_instagram
from twitter_api import post_to_twitter
from pinterest_api import post_to_pinterest
from medium_api import post_to_medium
from linkedin_api import post_to_linkedin

# Load environment variables from .env file
# Create a .env file in this directory and add your credentials.
# See .env.example for a template.
load_dotenv()

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
        created_at TEXT NOT NULL, FOREIGN KEY(platform_id) REFERENCES platforms(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, title TEXT NOT NULL,
        description TEXT, hashtags TEXT, media_path TEXT NOT NULL, schedule_time TEXT,
        status TEXT DEFAULT 'pending', error TEXT, created_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    )''')
    platforms = [
        ('youtube', 'YouTube'), ('instagram', 'Instagram'), ('twitter', 'Twitter'),
        ('pinterest', 'Pinterest'), ('medium', 'Medium'), ('linkedin', 'LinkedIn')
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
    conn = get_db()
    if request.method == 'POST':
        # Account creation is simplified. Credentials are now managed
        # via environment variables based on the account's database ID.
        data = request.form
        platform_id = data.get('platform_id')
        name = data.get('account_name')
        
        if not all([platform_id, name]):
            return jsonify({'error': 'Platform and Account Name are required.'}), 400

        try:
            c = conn.cursor()
            c.execute('INSERT INTO accounts (platform_id, name, created_at) VALUES (?, ?, ?)',
                      (platform_id, name, datetime.utcnow().isoformat()))
            conn.commit()
            flash(f"Account '{name}' created. Ensure you have set its credentials in the .env file.", "success")
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': f'Failed to create account: {e}'}), 500
        finally:
            conn.close()
    else: # GET
        platform_id = request.args.get('platform_id')
        query = 'SELECT * FROM accounts'
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
                # Parse the naive local time string
                local_time = isoparse(schedule_time_str)
                # Assume it's in the local timezone and convert to UTC
                utc_time = local_time.replace(tzinfo=tzlocal()).astimezone(timezone.utc)
                schedule_time_utc_iso = utc_time.isoformat()
            except ValueError as e:
                print(f"Error parsing schedule time '{schedule_time_str}': {e}")
                return jsonify({'error': f'Invalid schedule time format: {schedule_time_str}'}), 400

        # Verify account exists
        account = conn.execute('SELECT * FROM accounts WHERE id=?', 
                             (account_id,)).fetchone()
        if not account:
            return jsonify({'error': 'Invalid account'}), 400
            
        # Save media file
        if 'media' not in request.files:
            return jsonify({'error': 'No media file provided'}), 400
        file = request.files['media']
        uploads_dir = os.path.join(BASE_DIR, 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        media_path = os.path.join('uploads', f"{file.filename}")
        try:
            file.save(os.path.join(BASE_DIR, media_path))
        except Exception as e:
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
            
        try:
            c = conn.cursor()
            c.execute('''INSERT INTO content (account_id, title, description, hashtags, 
                         media_path, schedule_time, created_at) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (account_id, title, description, hashtags, 
                       media_path, schedule_time_utc_iso, created_at))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
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

@app.route('/authorize/youtube')
def authorize_youtube():
    client_secret_path_relative = request.args.get('client_secret_path')
    account_id = request.args.get('account_id')

    if not client_secret_path_relative or not account_id:
        return jsonify({'error': 'Missing parameters for YouTube authorization'}), 400

    client_secret_path_absolute = os.path.join(BASE_DIR, client_secret_path_relative)

    if not os.path.exists(client_secret_path_absolute):
        return jsonify({'error': 'Client secret file not found.' + client_secret_path_absolute}), 400

    try:
        # Create a Flow instance from the client secrets file
        flow = Flow.from_client_secrets_file(
            client_secret_path_absolute,
            scopes=SCOPES,
            # The callback URI must be registered in the Google Cloud Console
            # We use url_for to generate the correct callback URL dynamically
            redirect_uri=url_for('oauth2callback_youtube', _external=True, account_id=account_id)
        )

        # Generate the authorization URL and state
        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Request a refresh token
            include_granted_scopes='true')

        # Store the state in the session to verify in the callback
        # You need to set app.secret_key for session to work
        # session['oauth_state'] = state
        # For simplicity in this example, we are not using session state
        # In a real application, you MUST use state to prevent CSRF attacks.

        print(f'Redirecting for YouTube OAuth: {authorization_url}')

        # Redirect the user to the authorization URL
        return redirect(authorization_url)

    except Exception as e:
        print(f'Error initiating YouTube OAuth: {e}')
        # Update the account status to reflect the error
        conn = get_db()
        conn.execute("UPDATE accounts SET created_at=?, name='OAuth Error', credential_path=?, platform_id=? WHERE id=?", (datetime.utcnow().isoformat(), str(e), 0, account_id))
        conn.commit()
        conn.close()
        return jsonify({'error': f'Error initiating YouTube OAuth: {e}'}), 500

@app.route('/oauth2callback/youtube')
def oauth2callback_youtube():
    # This is the callback route after the user authorizes the app on Google
    account_id = request.args.get('account_id')
    # state = request.args.get('state') # In a real app, verify state with session['oauth_state']

    if not account_id:
        return jsonify({'error': 'Missing account ID in callback'}), 400

    conn = get_db()
    account = conn.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404

    # The temporary credential_path holds the path to the client_secret.json
    client_secret_path_relative = account['credential_path'].replace('_temp_', '')
    client_secret_path_absolute = os.path.join(BASE_DIR, client_secret_path_relative)

    if not os.path.exists(client_secret_path_absolute):
         conn.close()
         return jsonify({'error': 'Temporary client secret file not found during callback.' + client_secret_path_absolute}), 400

    try:
        # Re-create the flow instance
        flow = Flow.from_client_secrets_file(
            client_secret_path_absolute,
            scopes=[
                'https://www.googleapis.com/auth/youtube',
                'https://www.googleapis.com/auth/youtube.upload',
                'https://www.googleapis.com/auth/youtube.force-ssl'
            ],
            redirect_uri=url_for('oauth2callback_youtube', _external=True, account_id=account_id)
        )

        # Exchange the authorization code for credentials (tokens)
        authorization_response = request.url # Use the full request URL
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        flow.fetch_token(authorization_response=authorization_response)
        del os.environ['OAUTHLIB_INSECURE_TRANSPORT']

        creds = flow.credentials

        # Save the credentials to a file
        # Use a consistent naming convention, e.g., youtube_credentials_<account_id>.json
        credentials_filename = f'youtube_credentials_{account_id}.json'
        credentials_path_relative = os.path.join('uploads', credentials_filename)
        credentials_path_absolute = os.path.join(BASE_DIR, credentials_path_relative)

        with open(credentials_path_absolute, 'w') as token_file:
            token_file.write(creds.to_json())

        # Update the account entry in the database with the path to the saved credentials
        conn.execute('UPDATE accounts SET credential_path=? WHERE id=?', (credentials_path_relative, account_id))
        conn.commit()

        # Optionally, delete the temporary client_secret.json file
        try:
            os.remove(client_secret_path_absolute)
        except OSError as e:
            print(f"Error deleting temporary client secret file {client_secret_path_absolute}: {e}")

        conn.close()

        # Redirect to a success page or the dashboard
        flash('YouTube account linked successfully!', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f'Error handling YouTube OAuth callback: {e}')
        # Update the account status to reflect the error
        # Keep the temporary client_secret file for debugging if needed, or clean up.
        conn.execute("UPDATE accounts SET created_at=?, name='OAuth Callback Error', credential_path=? WHERE id=?", (datetime.utcnow().isoformat(), str(e), account_id))
        conn.commit()
        conn.close()
        flash(f'Error linking YouTube account: {e}', 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard even on error

# --- Delete Routes ---
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
    c = conn.cursor()
    try:
        # Optionally check for _method=DELETE
        # method = request.form.get('_method', '').upper()
        # if method != 'DELETE':
        #     return jsonify({'error': 'Method not allowed'}), 405

        # Optionally get media path before deleting content to delete the file
        # media_path_row = conn.execute('SELECT media_path FROM content WHERE id=?', (content_id,)).fetchone()
        # media_path = media_path_row['media_path'] if media_path_row else None

        c.execute('DELETE FROM content WHERE id=?', (content_id,))
        deleted_rows = c.rowcount
        conn.commit()
        conn.close()

        if deleted_rows == 0:
            return jsonify({'error': 'Content not found'}), 404

        # Optionally delete the media file
        # if media_path:
        #     try:
        #         os.remove(os.path.join(BASE_DIR, media_path))
        #         print(f"Deleted media file: {media_path}")
        #     except OSError as e:
        #         print(f"Error deleting media file {media_path}: {e}")

        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error deleting content {content_id}: {e}")
        return jsonify({'error': f'Failed to delete content: {str(e)}'}), 500

# --- Scheduler Setup ---
platform_apis = {
    'youtube': post_to_youtube,
    'instagram': post_to_instagram,
    'twitter': post_to_twitter,
    'pinterest': post_to_pinterest,
    'medium': post_to_medium,
    'linkedin': post_to_linkedin,
}

scheduler = BackgroundScheduler(timezone=timezone.utc)
scheduler.add_job(
    func=process_scheduled_posts,
    trigger='interval',
    minutes=1,
    args=[get_db, platform_apis, BASE_DIR]
)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, port=5000) 