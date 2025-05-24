
import os
import time
import re
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters
import logging

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

user_last_link_time = {}
user_link_clicks = {}
LINK_INTERVAL = 43200  # 12 hours
REQUIRED_ENGAGEMENTS = 5
link_pattern = re.compile(r'(https?://|www\.)\S+')

logging.basicConfig(level=logging.INFO)

def handle_message(update, context):
    message = update.message
    if not message or not message.text:
        return

    user = message.from_user
    chat = message.chat
    text = message.text.lower()
    user_id = user.id
    chat_id = chat.id
    current_time = time.time()

    try:
        admins = context.bot.get_chat_administrators(chat_id)
        if any(admin.user.id == user_id for admin in admins):
            return
    except Exception as e:
        logging.warning(f"Admin check failed: {e}")
        return

    if any(word in text for word in ["done", "clicked", "opened", "✅", "ok"]):
        clicks = user_link_clicks.get((chat_id, user_id), [])
        clicks = [t for t in clicks if current_time - t < LINK_INTERVAL]
        clicks.append(current_time)
        user_link_clicks[(chat_id, user_id)] = clicks
        return

    if link_pattern.search(text):
        last_post_time = user_last_link_time.get((chat_id, user_id), 0)
        clicks = user_link_clicks.get((chat_id, user_id), [])
        clicks = [t for t in clicks if current_time - t < LINK_INTERVAL]
        user_link_clicks[(chat_id, user_id)] = clicks

        if current_time - last_post_time < LINK_INTERVAL:
            try:
                message.delete()
                context.bot.send_message(chat_id=chat_id, text=f"⛔ {user.first_name}, you can only post 1 link every 12 hours.")
            except:
                pass
        elif len(clicks) < REQUIRED_ENGAGEMENTS:
            try:
                message.delete()
                context.bot.send_message(chat_id=chat_id, text=f"⚠️ {user.first_name}, open 5+ links in 12h before posting yours. Type 'done' after engaging.")
            except:
                pass
        else:
            user_last_link_time[(chat_id, user_id)] = current_time
            user_link_clicks[(chat_id, user_id)] = []

dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_message))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route("/")
def index():
    return "Bot running", 200

if __name__ == "__main__":
    app.run(port=5000)
