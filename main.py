import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ChatJoinRequestHandler

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Safely parse ADMIN_ID
admin_id_raw = os.getenv("ADMIN_ID")
try:
    ADMIN_ID = int(admin_id_raw)
    print(f"✅ Loaded ADMIN_ID: {ADMIN_ID}")
except:
    print(f"❌ Error loading ADMIN_ID: {admin_id_raw}")
    ADMIN_ID = None

# Get Log Channel ID
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# Track users
users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.add(user_id)
    await update.message.reply_text("Welcome to the channel bot!")
    
    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"👤 /start from user: {user_id}")

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat_join_request.chat.id
    user_id = update.chat_join_request.from_user.id
    await context.bot.approve_chat_join_request(chat_id, user_id)
    
    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"✅ Approved join request: {user_id}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    print(f"📢 Broadcast called by: {sender_id}")
    print(f"🔑 Expected ADMIN_ID: {ADMIN_ID}")

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

    result_msg = f"✅ Broadcast done. Sent: {success}, Failed: {fail}"
    await update.message.reply_text(result_msg)

    if LOG_CHANNEL_ID:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📢 Broadcast by {sender_id}:\n{message}\n\n{result_msg}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.run_polling()
