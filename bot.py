import praw
from dotenv import load_dotenv
import os
import time
import yaml
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

load_dotenv()

REDDIT_USERNAME = os.getenv('REDDIT_USERNAME')
REDDIT_PASSWORD = os.getenv('REDDIT_PASSWORD')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')

lock = threading.Lock()

try:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent='your_user_agent',
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD
    )
    print("Reddit instance initialized successfully. \n")
except Exception as e:
    print(f"Failed to initialize Reddit instance: {e} \n")
    exit(1)

try:
    with open('words.yaml', 'r') as file:
        config = yaml.safe_load(file)
except Exception as e:
    print(f"Failed to load YAML configuration: {e} \n")
    exit(1)

ids_file = 'scanned_ids.txt'
report_file = 'report.json'

try:
    with open(ids_file, 'r') as f:
        ids = set(f.read().splitlines())
except FileNotFoundError:
    ids = set()

trigger_words = config.get('trigger_words', [])
subreddit_names = config.get('sub_reddit', [])

def save_ids():
    """Save Scanned IDs to a file."""
    with lock:
        with open(ids_file, 'w') as f:
            for id in ids:
                f.write(f"{id}\n")

def write_report(data):
    """Save report data to a JSON file."""
    with lock:
        if os.path.exists(report_file):
            with open(report_file, 'r') as f:
                try:
                    reports = json.load(f)
                    if not isinstance(reports, list):
                        reports = []
                except json.JSONDecodeError:
                    reports = []
        else:
            reports = []
        reports.append(data)

        with open(report_file, 'w') as f:
            json.dump(reports, f, indent=4)



def scan_comments(subreddit_name):
    """Process comments in the subreddit and report based on trigger words."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        print(f"Accessing subreddit: {subreddit.display_name} \n")

        for comment in subreddit.stream.comments(skip_existing=True):
            if comment.id not in ids:
                matched_trigger_words = []

                for trigger_word in trigger_words:
                    if trigger_word in comment.body.lower():
                        matched_trigger_words.append(trigger_word)

                if matched_trigger_words:
                    if comment.author.name != REDDIT_USERNAME:
                        try:
                            user = comment.author.name
                            text = comment.body
                            comment_url = f"https://reddit.com{comment.permalink}"
                            print(f'Comment by {user}: {text} in {subreddit_name} \n')
                            print(f'Trigger Words: {", ".join(matched_trigger_words)} \n')
                            print(f'Link: {comment_url} \n')

                            report_data = {
                                "type": "comment",
                                "subreddit": subreddit_name,
                                "author": user,
                                "text": text,
                                "trigger_words": matched_trigger_words,
                                "url": comment_url,
                                "timestamp": str(datetime.utcnow())
                            }

                            write_report(report_data)

                            ids.add(comment.id)
                            save_ids()
                        except Exception as e:
                            print(f'\n Error scanning comment in {subreddit_name}: {e} \n')
    except Exception as e:
        print(f'\n Error accessing subreddit {subreddit_name}: {e} \n')

def scan_posts(subreddit_name):
    """Process posts in the subreddit and report based on trigger words."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        print(f"Accessing subreddit: {subreddit.display_name} \n")

        for submission in subreddit.stream.submissions(skip_existing=True):
            if submission.id not in ids:
                matched_trigger_words = []
                for trigger_word in trigger_words:
                    if trigger_word in submission.title.lower() or trigger_word in submission.selftext.lower():
                        matched_trigger_words.append(trigger_word)

                if matched_trigger_words:
                    if submission.author.name != REDDIT_USERNAME:
                        try:
                            title = submission.title
                            content = submission.selftext if submission.selftext.strip() else "No body text"
                            post_url = f"https://reddit.com{submission.permalink}"
                            print(f"Post Title: {title} in {subreddit_name} \n")
                            print(f"Post Body: {content} \n")
                            print(f"Link: {post_url} \n")
                            report_data = {
                                "type": "post",
                                "subreddit": subreddit_name,
                                "author": submission.author.name,
                                "title": title,
                                "content": content,
                                "trigger_words": matched_trigger_words,
                                "url": post_url,
                                "timestamp": str(datetime.utcnow())
                            }

                            write_report(report_data)
                            ids.add(submission.id)
                            save_ids()
                        except Exception as e:
                            print(f'\n Error scanning posts in {subreddit_name}: {e} \n')
    except Exception as e:
        print(f'\n Error accessing subreddit {subreddit_name}: {e} \n')

if __name__ == "__main__":
    print('Bot is running... \n')
    while True:
        with ThreadPoolExecutor(max_workers=len(subreddit_names) * 2) as executor:
            futures = []
            for name in subreddit_names:
                futures.append(executor.submit(scan_comments, name))
                futures.append(executor.submit(scan_posts, name))
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f'Error in bot loop: {e} \n')
        time.sleep(0.001)
