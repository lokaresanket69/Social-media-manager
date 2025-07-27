from datetime import datetime, timezone
import sqlite3
from dateutil.parser import isoparse
import os

def process_scheduled_posts(get_db, platform_apis, base_dir):
    """
    Checks for pending posts and processes them using the appropriate platform API function.
    """
    print(f"[Scheduler] Running scheduled posts check at {datetime.now(timezone.utc).isoformat()}")
    
    conn = get_db()
    try:
        # Fetch all pending posts and filter in Python to avoid string comparison issues
        pending_rows = conn.execute("SELECT * FROM content WHERE status='pending'").fetchall()
        due_posts = []
        now_utc = datetime.now(timezone.utc)
        for row in pending_rows:
            schedule_time_str = row['schedule_time']
            if not schedule_time_str:
                # No schedule specified – post immediately
                due_posts.append(row)
                continue
            try:
                sch_dt = isoparse(schedule_time_str)
                # Ensure timezone aware (treat naive as UTC)
                if sch_dt.tzinfo is None:
                    sch_dt = sch_dt.replace(tzinfo=timezone.utc)
                sch_dt_utc = sch_dt.astimezone(timezone.utc)
                if sch_dt_utc <= now_utc:
                    due_posts.append(row)
            except Exception as e:
                # Malformed timestamp – log and process anyway so it does not get stuck forever
                print(f"[Scheduler] Failed to parse schedule_time '{schedule_time_str}' for post ID {row['id']}: {e}. Processing immediately.")
                due_posts.append(row)

        if not due_posts:
            print("[Scheduler] No posts are due for processing.")
            return

        print(f"[Scheduler] Found {len(due_posts)} posts ready to be processed.")

        for post in due_posts:
            print(f"[Scheduler] Processing post ID: {post['id']}")
            
            # Set status to 'processing' to prevent reprocessing by other workers
            conn.execute("UPDATE content SET status='processing' WHERE id=?", (post['id'],))
            conn.commit()

            try:
                account = conn.execute('SELECT * FROM accounts WHERE id=?', (post['account_id'],)).fetchone()
                if not account:
                    raise Exception("Account not found.")

                platform = conn.execute('SELECT * FROM platforms WHERE id=?', (account['platform_id'],)).fetchone()
                if not platform:
                    raise Exception("Platform not found.")

                platform_name = platform['name']
                api_function = platform_apis.get(platform_name)

                # Convert all sqlite3.Row objects to dicts for robust access
                account_dict = dict(account)
                post_dict = dict(post)
                platform_dict = dict(platform)

                if api_function:
                    print(f"[Scheduler] Calling API for {platform_name} for post ID {post['id']}")
                    api_function(account_dict, post_dict, base_dir)
                    conn.execute("UPDATE content SET status='posted', error=NULL WHERE id=?", (post['id'],))
                    print(f"[Scheduler] Post ID {post['id']} successfully posted.")
                else:
                    raise Exception(f"No API function configured for platform: {platform_name}")

            except Exception as e:
                error_message = str(e)
                print(f"[Scheduler] Error processing post ID {post['id']}: {error_message}")
                conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (error_message, post['id']))
            
            # Commit the final status of the post ('posted' or 'error')
            conn.commit()

    except Exception as e:
        print(f"[Scheduler] A critical error occurred in the scheduler's main loop: {e}")
    finally:
        if conn:
            conn.close()
            print("[Scheduler] Database connection closed.")

# Note: The scheduler setup (BackgroundScheduler) is in app.py 