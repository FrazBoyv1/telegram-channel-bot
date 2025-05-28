import os
import asyncio
import logging
from pymongo import MongoClient
from telegram import Update, ChatMemberUpdated
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ENV Vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL"))
MONGO_URL = os.environ.get("MONGODB_URL")

# DB Setup
client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        users_col.update_one({"id": user.id}, {"$set": user.to_dict()}, upsert=True)
    await update.message.reply_text("👋 Hey! I'm your channel request manager bot.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    total_users = users_col.count_documents({})
    await update.message.reply_text(f"📊 Total users: {total_users}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to broadcast.")
        return

    msg = update.message.reply_to_message
    total = 0
    failed = 0

    for user in users_col.find():
        try:
            await context.bot.copy_message(chat_id=user["id"], from_chat_id=msg.chat_id, message_id=msg.message_id)
            total += 1
        except:
            failed += 1

    await update.message.reply_text(f"✅ Broadcasted to {total} users.\n❌ Failed: {failed}")

# Membership requests
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_join = update.chat_join_request
    await context.bot.approve_chat_join_request(chat_id=chat_join.chat.id, user_id=chat_join.from_user.id)
    await context.bot.send_message(chat_id=chat_join.from_user.id, text="✅ Your request to join the channel has been approved!")
    users_col.update_one({"id": chat_join.from_user.id}, {"$set": chat_join.from_user.to_dict()}, upsert=True)
    await context.bot.send_message(chat_id=LOG_CHANNEL, text=f"✅ Approved request from [{chat_join.from_user.first_name}](tg://user?id={chat_join.from_user.id})", parse_mode="Markdown")

# Log restart
async def notify_restart(bot_app):
    await bot_app.bot.send_message(chat_id=LOG_CHANNEL, text="🔄 Bot restarted and is now live!")

# Main function
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(ChatMemberHandler(join_request, ChatMemberHandler.CHAT_JOIN_REQUEST))

    await notify_restart(app)
    print("✅ Your service is live 🎉")
    await app.run_polling()

# Instead of asyncio.run()
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
