import praw
import time
import os
import json
import yaml
from datetime import datetime
import threading
import traceback

from dotenv import load_dotenv
load_dotenv()

REDDIT_USERNAME = ""
REDDIT_PASSWORD = ""
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent='Bot_adhd by /u/{}'.format(REDDIT_USERNAME),
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD
)

try:
    with open('words.yaml', 'r') as file:
        config = yaml.safe_load(file)
        trigger_words = config.get('trigger_words', [])
        if not trigger_words:
            raise ValueError("No trigger words found in the configuration file.")
except Exception as e:
    print(f"Error loading trigger words: {e}")
    exit(1)

subreddit_names = ["all"]

ids_file = 'scanned_ids.txt'
report_file = 'report.json'

try:
    with open(ids_file, 'r') as f:
        ids = set(f.read().splitlines())
except FileNotFoundError:
    ids = set()

def save_ids():
    with open(ids_file, 'w') as f:
        for id in ids:
            f.write(f"{id}\n")

def write_report(data):
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

def scan_comments():
    subreddit = reddit.subreddit("all") 
    print("Bot is running on comments...\n")
    try:
        for comment in subreddit.stream.comments(skip_existing=True):
            if comment.id not in ids:
                matched_trigger_words = []
                for trigger_word in trigger_words:
                    if trigger_word in comment.body.lower():
                        matched_trigger_words.append(trigger_word)

                if matched_trigger_words:
                    if comment.author and comment.author.name != reddit.user.me():
                        try:
                            user = comment.author.name
                            text = comment.body
                            comment_url = f"https://reddit.com{comment.permalink}"
                            print(f'Comment by {user}: {text} in {comment.subreddit.display_name}')
                            print(f'Trigger Words: {", ".join(matched_trigger_words)}')
                            print(f'Link: {comment_url}\n')

                            report_data = {
                                "type": "comment",
                                "subreddit": comment.subreddit.display_name,
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
                            print(f"Error processing comment: {e}")
    except Exception as e:
        print(f"Error accessing subreddit comments: {e}")
        raise

def scan_posts():
    subreddit = reddit.subreddit("all")
    print("Bot is running on posts...\n")
    try:
        for submission in subreddit.stream.submissions(skip_existing=True):
            if submission.id not in ids:
                matched_trigger_words = []
                for trigger_word in trigger_words:
                    if trigger_word in submission.title.lower() or trigger_word in submission.selftext.lower():
                        matched_trigger_words.append(trigger_word)

                if matched_trigger_words:
                    if submission.author and submission.author.name != reddit.user.me():
                        try:
                            title = submission.title
                            content = submission.selftext if submission.selftext.strip() else "No body text"
                            post_url = f"https://reddit.com{submission.permalink}"
                            print(f"Post Title: {title} in {submission.subreddit.display_name}")
                            print(f"Post Body: {content}")
                            print(f"Link: {post_url}\n")

                            report_data = {
                                "type": "post",
                                "subreddit": submission.subreddit.display_name,
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
                            print(f"Error processing post: {e}")
    except Exception as e:
        print(f"Error accessing subreddit posts: {e}")
        raise

def run_stream(scan_function):
    backoff = 1
    max_backoff = 300

    while True:
        try:
            scan_function()
        except Exception as e:
            print(f"Error in {scan_function.__name__}: {e}")
            traceback.print_exc()
            if '429' in str(e):
                print(f"Rate limited, backing off for {backoff} seconds...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            else:
                time.sleep(5)
        else:
            backoff = 1

if __name__ == "__main__":
    comment_thread = threading.Thread(target=run_stream, args=(scan_comments,), daemon=True)
    post_thread = threading.Thread(target=run_stream, args=(scan_posts,), daemon=True)

    comment_thread.start()
    post_thread.start()

    while True:
        time.sleep(60)
