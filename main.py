import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ChatJoinRequestHandler, ContextTypes
)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users.add(user.id)
    await update.message.reply_text("Hey! You are registered.")

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.chat_join_request.approve()
    user = update.chat_join_request.from_user
    users.add(user.id)
    await context.bot.send_message(chat_id=user.id, text="Welcome! Your request was approved.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return

    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return

    success, fail = 0, 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except:
            fail += 1

    await update.message.reply_text(f"Broadcast done. ✅: {success}, ❌: {fail}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(ChatJoinRequestHandler(join_request))

    app.run_polling()

if __name__ == "__main__":
    main()
