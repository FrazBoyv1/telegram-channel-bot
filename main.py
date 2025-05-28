import os
import logging
import asyncio
from datetime import datetime
from pymongo import MongoClient
from telegram import Update, ChatMemberUpdated
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load ENV variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
LOG_CHANNEL = os.environ.get("LOG_CHANNEL")
MONGODB_URL = os.environ.get("MONGODB_URL")

# MongoDB Setup
client = MongoClient(MONGODB_URL)
db = client["telegram_bot"]
users_collection = db["users"]

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("Hello! I'm your channel bot 🤖")
    await log_msg(f"🟢 Bot started by [{user.full_name}](tg://user?id={user.id})")

# /broadcast command (reply to message)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != os.environ.get("OWNER_ID"):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to a message to broadcast.")
        return

    sent = 0
    failed = 0
    msg = update.message.reply_to_message
    users = users_collection.find()
    for user in users:
        try:
            await context.bot.copy_message(chat_id=user["user_id"], from_chat_id=msg.chat.id, message_id=msg.message_id)
            sent += 1
            await asyncio.sleep(0.3)
        except Exception:
            failed += 1
            continue

    await update.message.reply_text(f"✅ Sent: {sent}, ❌ Failed: {failed}")

# /stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = users_collection.count_documents({})
    await update.message.reply_text(f"📊 Total users: {count}")

# New member join handler
async def accept_request(update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_member.new_chat_member.status == "member":
        user = update.chat_member.from_user
        await context.bot.send_message(chat_id=user.id, text="✅ Your request to join the channel has been approved!")

        # Save user to DB
        users_collection.update_one(
            {"user_id": user.id},
            {"$set": {"user_id": user.id, "name": user.full_name, "joined": str(datetime.now())}},
            upsert=True
        )

        await log_msg(f"✅ Approved: [{user.full_name}](tg://user?id={user.id})")

# Log messages to log channel
async def log_msg(text):
    if LOG_CHANNEL:
        try:
            await app.bot.send_message(chat_id=LOG_CHANNEL, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

# Keep-alive web server (only needed for Web Service on Render)
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    logger.info(f"🟢 Keep-alive server running on port {port}")
    server.serve_forever()

# Run the bot
if __name__ == '__main__':
    threading.Thread(target=run_server).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(ChatMemberHandler(accept_request, ChatMemberHandler.CHAT_MEMBER))

    asyncio.run(log_msg("🔄 Bot restarted"))
    app.run_polling()
