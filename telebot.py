from telethon.sync import TelegramClient, events
import json
import os

API_ID = ''
API_HASH = ''
SESSION_NAME = 'scraper_session'

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

all_messages = []

def create_json_file():
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        print(f"[INFO] Created new JSON file: {OUTPUT_FILE}")

async def fetch_past_messages():
    print("[INFO] Fetching past messages...")
    count = 0
    async for message in client.iter_messages(GROUP_USERNAME, reverse=True):
        if message.text:
            message_url = f"https://t.me/{GROUP_USERNAME[1:]}/{message.id}"

            reply_to_msg_id = message.reply_to_msg_id if message.reply_to_msg_id else None
            
            msg = {
                'id': message.id,
                'text': message.text,
                'date': str(message.date),
                'username': message.sender.username if message.sender and message.sender.username else None,
                'reply_to_msg_id': reply_to_msg_id
            }
            all_messages.append(msg)
            count += 1
    print(f"[INFO] Fetched {count} past messages.")

def save_messages_to_file():
    with open(OUTPUT_FILE, 'r+', encoding='utf-8') as f:
        existing_messages = json.load(f)
        existing_messages.extend(all_messages)
        f.seek(0)
        json.dump(existing_messages, f, ensure_ascii=False, indent=4)
    print(f"[INFO] Saved {len(all_messages)} new messages to {OUTPUT_FILE}.")
    all_messages.clear()

@client.on(events.NewMessage(chats=GROUP_USERNAME))
async def new_message_handler(event):
    message = event.message
    if message.text:
        print(f"[NEW MESSAGE] {message.text}")

        message_url = f"https://t.me/{GROUP_USERNAME[1:]}/{message.id}"

        reply_to_msg_id = message.reply_to_msg_id if message.reply_to_msg_id else None
        
        msg = {
            'id': message.id,
            'text': message.text,
            'date': str(message.date),
            'username': message.sender.username if message.sender and message.sender.username else None,
            'reply_to_msg_id': reply_to_msg_id
        }
        all_messages.append(msg)
        save_messages_to_file()

async def main():
    create_json_file()

    await fetch_past_messages()
    save_messages_to_file()

    print("[INFO] Listening for new messages...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    GROUP_USERNAME = ''
    OUTPUT_FILE = 'messages.json'
    with client:
        client.loop.run_until_complete(main())
