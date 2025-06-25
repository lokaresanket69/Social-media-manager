from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone
import json
from dateutil.parser import isoparse
from dateutil.tz import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler
from security import encrypt_data, decrypt_data

# --- Local API Modules ---
from scheduler import process_scheduled_posts
from youtube_api import post_to_youtube
# from instagram_api import post_to_instagram
from twitter_api import post_to_twitter
from pinterest_api import post_to_pinterest
from medium_api import post_to_medium
from linkedin_api import post_to_linkedin

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
        data = request.form
        platform_id = data.get('platform_id')
        name = data.get('account_name')
        credentials = {key: value for key, value in data.items() if key not in ['platform_id', 'account_name']}
        if not all([platform_id, name, credentials]):
            return jsonify({'error': 'Platform, Account Name, and Credentials are required.'}), 400
        try:
            c = conn.cursor()
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

# The old YouTube OAuth routes (authorize_youtube, oauth2callback_youtube) are no longer needed
# as credentials are now added directly in the 'Add Account' form. They have been removed.

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
    # 'instagram': post_to_instagram,  # Temporarily disabled
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