import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ChatJoinRequestHandler,
)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# Convert ADMIN_ID safely to int
admin_id_raw = os.getenv("ADMIN_ID")
try:
    ADMIN_ID = int(admin_id_raw)
    print(f"✅ Loaded ADMIN_ID: {ADMIN_ID}")
except:
    print(f"❌ Invalid ADMIN_ID: {admin_id_raw}")
    ADMIN_ID = None

# Load users from file or start with empty set
if os.path.exists("users.json"):
    with open("users.json", "r") as f:
        users = set(json.load(f))
else:
    users = set()

# Function to save users to users.json
def save_users():
    with open("users.json", "w") as f:
        json.dump(list(users), f)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users.add(user_id)
        save_users()
        if LOG_CHANNEL_ID:
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🆕 New user: {user_id}")
    await update.message.reply_text("Welcome to the channel bot!")

# Auto-approve join requests
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat_join_request.chat.id
    user_id = update.chat_join_request.from_user.id
    await context.bot.approve_chat_join_request(chat_id, user_id)
    
    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"✅ Approved: {user_id}")

# /broadcast command (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    if sender_id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return

    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("⚠️ Usage: /broadcast Your message here")
        return

    success, fail = 0, 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except:
            fail += 1

    result_msg = f"📢 Broadcast complete:\n✅ Sent: {success}\n❌ Failed: {fail}"
    await update.message.reply_text(result_msg)

    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📢 Broadcast by {sender_id}:\n{message}\n\n{result_msg}")

# Run the bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Log restart/startup to channel
    async def on_startup(app):
        print("🚀 Bot started successfully!")
        if LOG_CHANNEL_ID:
            try:
                await app.bot.send_message(chat_id=LOG_CHANNEL_ID, text="✅ Bot started successfully!")
            except Exception as e:
                print(f"❌ Could not send log start message: {e}")

    app.post_init = on_startup
    app.run_polling()
