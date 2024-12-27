import praw
from dotenv import load_dotenv
import os
import json
import threading

load_dotenv()

REDDIT_USERNAME = ""
REDDIT_PASSWORD = ""
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""

lock = threading.Lock()

try:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent='MyRedditBot/0.1 by YourUsername',
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD
    )
    print("Reddit instance initialized successfully.\n")
except Exception as e:
    print(f"Failed to initialize Reddit instance: {e}\n")
    exit(1)

def write_report(data, file_path):
    """Save data to a JSON file."""
    with lock:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                try:
                    reports = json.load(f)
                    if not isinstance(reports, list):
                        reports = []
                except json.JSONDecodeError:
                    reports = []
        else:
            reports = []

        reports.append(data)

        with open(file_path, 'w') as f:
            json.dump(reports, f, indent=4)

def scan_user_comments(username, comment_report_file):
    """Collect all comments made by the user across all subreddits."""
    try:
        user = reddit.redditor(username)
        user.comments.top(limit=1)
        print(f"Accessing all comments by user: {username}\n")

        for comment in user.comments.top(limit=None):
            try:
                if comment.body == "[deleted]":
                    print(f"Skipping deleted comment {comment.id}")
                    continue

                comment_url = f"https://reddit.com{comment.permalink}"

                report_data = {
                    "type": "comment",
                    "author": username,
                    "text": comment.body,
                    "url": comment_url,
                }

                write_report(report_data, comment_report_file)
                print(f"Collected comment: {comment.body}\n")
                print(f"Comment Link: {comment_url}\n")

            except praw.exceptions.PRAWException as e:
                print(f"Error processing comment {comment.id}: {e}")

    except Exception as e:
        print(f"Error accessing comments by user {username}: {e}\n")

def scan_user_posts(username, post_report_file):
    """Collect all submissions made by the user across all subreddits."""
    try:
        user = reddit.redditor(username)
        user.submissions.top(limit=1)
        print(f"Accessing all posts by user: {username}\n")

        for submission in user.submissions.top(limit=None):
            try:
                if submission.selftext == "[deleted]":
                    print(f"Skipping deleted post {submission.id}")
                    continue

                post_url = f"https://reddit.com{submission.permalink}"
                submission_data = {
                    "type": "post",
                    "author": username,
                    "title": submission.title,
                    "text": submission.selftext,
                    "url": post_url,
                    "subreddit": submission.subreddit.display_name,
                    "score": submission.score,
                    "num_comments": submission.num_comments
                }

                write_report(submission_data, post_report_file)
                print(f"Collected post: {submission.title}\n")
                print(f"Post Link: {post_url}\n")

            except praw.exceptions.PRAWException as e:
                print(f"Error processing post {submission.id}: {e}")

    except Exception as e:
        print(f"Error accessing posts by user {username}: {e}\n")

if __name__ == "__main__":
    print("Bot is running...\n")
    if not REDDIT_USERNAME:
        print("Please provide a valid Reddit username in the environment variables.\n")
    else:
        u = input("Intel Collection For User:")
        report_file = 'userdata/user_data'+str(u)+'.json'
        scan_user_comments(u, report_file)
        scan_user_posts(u, report_file)
