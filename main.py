from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import openai
import logging
import os

# Logging to track errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# API keys
TELEGRAM_TOKEN = '7637325032:AAGQhgDBbPYEtqaod6iAuqHJu5Pfl2OaLo4'
OPENAI_KEY = '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'

openai.api_key = OPENAI_KEY

# Error handling function
def error(update: Update, context: CallbackContext):
    logging.warning(f'Update {update} caused error {context.error}')
    update.message.reply_text("⚠️ Error ho gaya. Please thodi der baad try kariye!")

# Message handler
def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text

    try:
        # OpenAI se response lena
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_message}]
        )
        ai_reply = response['choices'][0]['message']['content']
        
        # Bot reply karega
        update.message.reply_text(ai_reply)

    except Exception as e:
        logging.error(f"Error: {e}")
        update.message.reply_text("⚠️ Koi error ho gaya. Please thoda wait kariye!")

# Main function
def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_error_handler(error)

    # Start the bot
    updater.start_polling()
    logging.info("Bot started...")
    updater.idle()

if __name__ == '__main__':
    main()
