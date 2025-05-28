import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ChatJoinRequestHandler,
)
from pymongo import MongoClient

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
MONGODB_URL = os.getenv("MONGODB_URL")
admin_id_raw = os.getenv("ADMIN_ID")

try:
    ADMIN_ID = int(admin_id_raw)
except:
    ADMIN_ID = None
    print("❌ Invalid ADMIN_ID")

# Connect to MongoDB
mongo = MongoClient(MONGODB_URL)
db = mongo["telegram_bot"]
users_col = db["users"]

# Save user if not exists or update username
def add_user(user_id: int, username: str = None):
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id, "username": username})
        print(f"➕ New user added: {user_id} (@{username})")
    else:
        users_col.update_one({"_id": user_id}, {"$set": {"username": username}})

# Get all user IDs
def get_all_users():
    return [doc["_id"] for doc in users_col.find()]

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username)

    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🆕 New user: {user.id} (@{user.username})")

    await update.message.reply_text("👋 Welcome! You’re now connected with the bot.")

# Join request handler
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    user_id = req.from_user.id
    username = req.from_user.username or "NoUsername"

    await context.bot.approve_chat_join_request(req.chat.id, user_id)
    add_user(user_id, username)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Your request to join the channel has been approved! Welcome!"
        )
        print(f"📩 Sent welcome message to {user_id} (@{username})")
    except Exception as e:
        print(f"❌ Failed to send welcome message to {user_id} - {e}")
        if LOG_CHANNEL_ID:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"⚠️ Could not DM {user_id} (@{username}) after approval. Error: {e}"
            )

    if LOG_CHANNEL_ID:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"✅ Approved user: {user_id} (@{username})"
        )

# /broadcast command
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You’re not authorized to use this command.")
        return

    users = get_all_users()
    success, fail = 0, 0
    sent_type = "text"

    if update.message.reply_to_message:
        original = update.message.reply_to_message
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=original.message_id)
                success += 1
            except:
                fail += 1
        sent_type = "forward"
    else:
        message = ' '.join(context.args)
        if not message:
            await update.message.reply_text("⚠️ Usage: reply to a message or use /broadcast <text>")
            return
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=message)
                success += 1
            except:
                fail += 1

    msg = f"📢 Broadcast ({sent_type}) completed:\n✅ Sent: {success}\n❌ Failed: {fail}"
    await update.message.reply_text(msg)
    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📢 Broadcast log\n{msg}")

# /stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized access.")
        return

    count = users_col.count_documents({})
    await update.message.reply_text(f"📊 Total users: {count}")
    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📈 /stats command used: {count} users")

# /users command
async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized access.")
        return

    users = get_all_users()
    if not users:
        await update.message.reply_text("No users found.")
        return

    user_list = "\n".join(str(uid) for uid in users)
    if len(user_list) > 4000:
        with open("user_ids.txt", "w") as f:
            f.write(user_list)
        await update.message.reply_document(document=open("user_ids.txt", "rb"))
    else:
        await update.message.reply_text(f"👥 Users ({len(users)}):\n\n{user_list}")

    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text="📤 /users command executed.")

# Run bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("users", users_list))

    async def on_startup(app):
        print("✅ Bot started.")
        if LOG_CHANNEL_ID:
            try:
                await app.bot.send_message(chat_id=LOG_CHANNEL_ID, text="🚀 Bot has restarted and is running.")
            except Exception as e:
                print(f"⚠️ Log channel failed: {e}")

    app.post_init = on_startup
    app.run_polling()
