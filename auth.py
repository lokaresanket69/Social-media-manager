from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('social_media_automation.db')
        conn.row_factory = sqlite3.Row
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['email'], user['password_hash'])
        return None

    @staticmethod
    def create(username, email, password):
        conn = sqlite3.connect('social_media_automation.db')
        password_hash = generate_password_hash(password)
        created_at = datetime.utcnow().isoformat()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                        (username, email, password_hash, created_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    @staticmethod
    def authenticate(email, password):
        conn = sqlite3.connect('social_media_automation.db')
        conn.row_factory = sqlite3.Row
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            return User(user['id'], user['username'], user['email'], user['password_hash'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def init_auth(app):
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Create users table if it doesn't exist
    conn = sqlite3.connect('social_media_automation.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    conn.commit()
    conn.close() 