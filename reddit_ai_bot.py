import os
import json
import time
import torch
import requests
from dotenv import load_dotenv
import praw
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

load_dotenv()

REDDIT_USERNAME = 'REDDIT_USERNAME'
REDDIT_PASSWORD = 'REDDIT_PASSWORD'
REDDIT_CLIENT_ID = 'REDDIT_CLIENT_ID'
REDDIT_CLIENT_SECRET = 'REDDIT_CLIENT_SECRET'

REPORT_FILE = 'report.json'
REPLIED_FILE = 'replied_ids.txt'

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent='deepseek_local_replier',
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

print("Loading DeepSeek model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device=0 if device == "cuda" else -1)
print("Model loaded.\n")


def generate_reply(text):
    prompt = f"[INST]You're a helpful Reddit assistant. Reply to the following:\n{text}\n[/INST]"
    try:
        output = generator(prompt, max_new_tokens=200, do_sample=True, temperature=0.7)[0]["generated_text"]
        return output.split("[/INST]")[-1].strip()
    except Exception as e:
        print(f"Generation error: {e}")
        return None


def save_replied_id(item_id):
    replied_ids.add(item_id)
    with open(REPLIED_FILE, 'w') as f:
        for rid in replied_ids:
            f.write(f"{rid}\n")


def reply_to_item(item):
    try:
        item_type = item["type"]
        url = item["url"]
        content = item.get("text") or item.get("content")
        reply_text = generate_reply(content)

        if not reply_text:
            return

        if item_type == "comment":
            comment_id = url.split("/")[-1]
            comment = reddit.comment(comment_id)
            comment.reply(reply_text)
            print(f"Replied to comment {comment_id}")
            save_replied_id(comment_id)

        elif item_type == "post":
            submission_id = url.split("/")[-3]
            submission = reddit.submission(submission_id)
            submission.reply(reply_text)
            print(f"Replied to post {submission_id}")
            save_replied_id(submission_id)

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
                        time.sleep(10)
                        continue
                except json.JSONDecodeError:
                    time.sleep(10)
                    continue

            for item in reports:
                item_id = item["url"].split("/")[-1]
                if item_id not in replied_ids:
                    reply_to_item(item)
                    time.sleep(15)

        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(20)


if __name__ == "__main__":
    monitor_reports()
