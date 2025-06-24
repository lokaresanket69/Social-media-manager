from datetime import datetime, timezone
import sqlite3
from dateutil.parser import isoparse
import os

def process_scheduled_posts(get_db, post_to_youtube, post_to_instagram, post_to_twitter, PinterestAPI, MediumAPI, QuoraAPI, LinkedInAPI, base_dir):
    conn = get_db()
    # Use timezone-aware datetime (UTC)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    print(f"[Scheduler] Running scheduled posts check at {now_iso}")

    rows = conn.execute("SELECT * FROM content WHERE status='pending'").fetchall()
    print(f"[Scheduler] Found {len(rows)} posts with status 'pending'.")

    posts_to_process = []
    for row in rows:
        schedule_time_str = row['schedule_time']
        if schedule_time_str:
            try:
                # Attempt to parse the schedule_time string into a datetime object
                schedule_time = isoparse(schedule_time_str)

                # If the parsed datetime is naive, assume UTC for comparison
                if schedule_time.tzinfo is None:
                    schedule_time = schedule_time.replace(tzinfo=timezone.utc)

                # Compare timezone-aware datetimes
                if schedule_time <= now:
                    posts_to_process.append(row)
                else:
                    print(f"[Scheduler] Post ID {row['id']} scheduled for {schedule_time_str} is in the future ({schedule_time} > {now}).")

            except ValueError as e:
                # Handle cases where schedule_time string is not a valid ISO format
                print(f"[Scheduler] Skipping post ID {row['id']}: Invalid schedule_time format '{schedule_time_str}' - {e}")
                conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (f"Invalid schedule time format: {schedule_time_str}", row['id']))
                conn.commit() # Commit immediately for errors found during parsing
        else:
            # Handle posts with no schedule_time set (shouldn't be 'pending' usually, but as a safeguard)
            print(f"[Scheduler] Skipping post ID {row['id']}: No schedule_time set.")
            conn.execute("UPDATE content SET status='error', error='No schedule_time set' WHERE id=?", (row['id'],))
            conn.commit()

    print(f"[Scheduler] Identified {len(posts_to_process)} pending posts to process after time check.")

    for row in posts_to_process:
        print(f"[Scheduler] Processing post ID: {row['id']} scheduled for {row['schedule_time']}")
        account = conn.execute('SELECT * FROM accounts WHERE id=?', (row['account_id'],)).fetchone()
        platform = conn.execute('SELECT * FROM platforms WHERE id=?', (account['platform_id'],)).fetchone()

        if not account or not platform:
            print(f"[Scheduler] Skipping post {row['id']}: Account or Platform not found.")
            conn.execute("UPDATE content SET status='error', error='Account or Platform not found' WHERE id=?", (row['id'],))
            conn.commit() # Commit immediately for errors
            continue

        try:
            print(f"[Scheduler] Attempting to post content ID {row['id']} to {platform['name']} using account {account['name']}")
            if platform['name'] == 'youtube':
                # Need to pass the full content row including media_path, title, etc.
                post_to_youtube(account, row, base_dir)
            elif platform['name'] == 'instagram':
                post_to_instagram(account, row)
            elif platform['name'] == 'twitter':
                post_to_twitter(account, row)
            elif platform['name'] == 'pinterest':
                pinterest_api = PinterestAPI(access_token=account['credential_path'])
                # For Pinterest, 'media_path' is critical. 'description' is used for pin description
                # and 'title' for pin title. 'hashtags' can be appended to description.
                # Assuming `media_path` is relative to `base_dir`.
                full_media_path = os.path.join(base_dir, row['media_path'])
                pinterest_api.post_pin(
                    board_id=account['name'], # Assuming account name stores board ID or relevant identifier
                    title=row['title'],
                    description=f"{row['description']} {row['hashtags'] or ''}",
                    image_path=full_media_path
                )
            elif platform['name'] == 'medium':
                medium_api = MediumAPI(access_token=account['credential_path'])
                # For Medium, 'title' is for the story title, 'description' for content.
                # 'hashtags' can be passed as tags.
                medium_api.post_story(
                    title=row['title'],
                    content=row['description'], # Assuming description holds the main content
                    tags=[tag.strip() for tag in row['hashtags'].split(',')] if row['hashtags'] else []
                )
            elif platform['name'] == 'quora':
                quora_api = QuoraAPI(access_token=account['credential_path'])
                # For Quora, 'title' is for the question/topic, 'description' for the answer content.
                # 'hashtags' can be used for topics.
                quora_api.post_content(
                    title=row['title'], # Can be used as question or part of content
                    content=row['description'],
                    topics=[topic.strip() for topic in row['hashtags'].split(',')] if row['hashtags'] else []
                )
            elif platform['name'] == 'linkedin':
                linkedin_api = LinkedInAPI(access_token=account['credential_path'])
                # For LinkedIn, 'description' is the main text content.
                # If there's a media file, it needs to be uploaded first.
                if row['media_path']:
                    full_media_path = os.path.join(base_dir, row['media_path'])
                    asset_urn = linkedin_api.upload_media(full_media_path)
                    if asset_urn:
                        # This part would need more sophisticated logic to create a rich media post
                        # For simplicity, we are just posting text for now if media is present.
                        # A more complete implementation would update the payload to include media.
                        print(f"[Scheduler] LinkedIn media uploaded: {asset_urn}. Posting as text for now.")
                        linkedin_api.post_content(text=f"{row['title']}\n\n{row['description']} {row['hashtags'] or ''}")
                    else:
                        print(f"[Scheduler] Failed to upload media to LinkedIn for post {row['id']}. Posting text only.")
                        linkedin_api.post_content(text=f"{row['title']}\n\n{row['description']} {row['hashtags'] or ''}")
                else:
                    linkedin_api.post_content(text=f"{row['title']}\n\n{row['description']} {row['hashtags'] or ''}")

            print(f"[Scheduler] Post ID {row['id']} processed successfully. Updating status to 'posted'.")
            conn.execute("UPDATE content SET status='posted', error=NULL WHERE id=?", (row['id'],))
            # Commit after each successful post to update status immediately
            conn.commit()

        except Exception as e:
            error_message = str(e)
            print(f"[Scheduler] Error processing post ID {row['id']}: {error_message}")
            conn.execute("UPDATE content SET status='error', error=? WHERE id=?", (error_message, row['id']))
            # Commit after each failed post to update status and error message
            conn.commit()

    # No need for a final commit here as we are committing inside the loop
    conn.close()

# Note: The scheduler setup (BackgroundScheduler) is in app.py 