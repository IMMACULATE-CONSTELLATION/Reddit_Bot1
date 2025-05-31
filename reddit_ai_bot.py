import os
import json
import time
import torch
from dotenv import load_dotenv
import praw
from praw.exceptions import APIException
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import re

load_dotenv()


REDDIT_USERNAME = ""
REDDIT_PASSWORD = ""
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""

REPORT_FILE = 'report.json'
REPLIED_FILE = 'replied_ids.txt'

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent='Bot_adhd',
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD
)

try:
    with open(REPLIED_FILE, 'r') as f:
        replied_ids = set(f.read().splitlines())
except FileNotFoundError:
    replied_ids = set()

MODEL_NAME = "deepseek-ai/deepseek-llm-67b-chat"
device = "cuda" if torch.cuda.is_available() else "cpu"

print("Loading LLM model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

print("Model loaded.\n")

def generate_reply(text):
    prompt = f"You're a helpful Reddit assistant. Reply to the following:\n{text}\n"
    try:
        output = generator(prompt, max_new_tokens=100, do_sample=True, temperature=0.7)[0]["generated_text"]
        return output[len(prompt):].strip()
    except Exception as e:
        print(f"Generation error: {e}")
        return None

def save_replied_id(item_id):
    replied_ids.add(item_id)
    with open(REPLIED_FILE, 'w') as f:
        for rid in replied_ids:
            f.write(f"{rid}\n")

def extract_id_from_url(url, item_type):
    if item_type == "comment":
        match = re.search(r'comments/\w+/\w+/(\w+)', url)
        if match:
            return match.group(1)
        parts = url.rstrip('/').split('/')
        if parts[-1].isalnum():
            return parts[-1]
    elif item_type == "post":
        match = re.search(r'comments/(\w+)', url)
        if match:
            return match.group(1)
    return None

def reply_to_item(item):
    try:
        item_type = item.get("type")
        url = item.get("url")
        content = item.get("text") or item.get("content")
        if not (item_type and url and content):
            print("Skipping item with missing type, url, or content.")
            return

        reply_text = generate_reply(content)
        if not reply_text:
            print("No reply generated.")
            return

        if item_type == "comment":
            comment_id = extract_id_from_url(url, "comment")
            if not comment_id:
                print(f"Invalid comment ID extracted from URL: {url}")
                return
            comment = reddit.comment(comment_id)
            try:
                comment.reply(reply_text)
                print(f"Replied to comment {comment_id}")
                save_replied_id(comment_id)
            except APIException as e:
                print(f"PRAW API Exception replying to comment {comment_id}: {e.error_type} - {e.message}")

        elif item_type == "post":
            submission_id = extract_id_from_url(url, "post")
            if not submission_id:
                print(f"Invalid post ID extracted from URL: {url}")
                return
            submission = reddit.submission(submission_id)
            try:
                submission.reply(reply_text)
                print(f"Replied to post {submission_id}")
                save_replied_id(submission_id)
            except APIException as e:
                print(f"PRAW API Exception replying to post {submission_id}: {e.error_type} - {e.message}")

    except Exception as e:
        print(f"Error replying: {e}")

def monitor_reports():
    print("Monitoring report.json...\n")
    while True:
        try:
            if not os.path.exists(REPORT_FILE):
                time.sleep(10)
                continue

            with open(REPORT_FILE, 'r') as f:
                try:
                    reports = json.load(f)
                    if not isinstance(reports, list):
                        print("Report file does not contain a list. Waiting...")
                        time.sleep(10)
                        continue
                except json.JSONDecodeError:
                    print("Report file contains invalid JSON. Waiting...")
                    time.sleep(10)
                    continue

            for item in reports:
                item_id = extract_id_from_url(item.get("url", ""), item.get("type", ""))
                if not item_id:
                    print(f"Skipping item with invalid or missing ID: {item}")
                    continue
                if item_id not in replied_ids:
                    reply_to_item(item)
                    time.sleep(1)

        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(20)

if __name__ == "__main__":
    monitor_reports()
