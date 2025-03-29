import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from openai import OpenAI
from io import BytesIO

# ✅ Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_UPLOAD_PRESET = "ml_default"

# ✅ OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ User session dictionary to manage mode
user_modes = {}

# ✅ Cloudinary Upload Function
def upload_to_cloudinary(image_bytes):
    """Uploads image to Cloudinary and returns the URL"""
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    files = {'file': image_bytes}
    data = {"upload_preset": CLOUDINARY_UPLOAD_PRESET}

    try:
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            image_url = response.json().get("secure_url")
            logger.info(f"Image uploaded successfully: {image_url}")
            return image_url
        else:
            logger.error(f"Failed to upload image: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during upload: {str(e)}")
        return None


# ✅ Mode Switching Menu
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mode selection buttons"""
    keyboard = [
        [InlineKeyboardButton("🖼️ Image-to-Image", callback_data="image_to_image")],
        [InlineKeyboardButton("📝 Text-to-Image", callback_data="text_to_image")],
        [InlineKeyboardButton("💬 Chat Mode", callback_data="chat")],
        [InlineKeyboardButton("❌ Exit", callback_data="exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✨ Would you like to try another mode or continue chatting?", reply_markup=reply_markup)


# ✅ Handle mode switching
async def mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mode selection"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    mode = query.data

    if mode == "exit":
        user_modes.pop(user_id, None)
        await query.edit_message_text("✅ Exited. You can start over anytime.")
    else:
        user_modes[user_id] = mode
        await query.edit_message_text(f"✅ Mode switched to: {mode.replace('_', ' ').title()}.")
        

# ✅ Chat Mode Handler
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles regular chat messages"""
    user_id = update.effective_user.id

    if user_modes.get(user_id) != "chat":
        await show_menu(update, context)
        return

    user_input = update.message.text

    # OpenAI Chat API
    try:
        response = client.chat_completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        reply = response.choices[0].message["content"]
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        await update.message.reply_text("❌ Failed to generate a response.")


# ✅ Text-to-Image Mode
async def handle_text_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text-to-image generation"""
    user_id = update.effective_user.id

    if user_modes.get(user_id) != "text_to_image":
        await show_menu(update, context)
        return

    prompt = update.message.text

    await update.message.reply_text("⏳ Generating image... Please wait.")
    
    try:
        response = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", n=1)
        image_url = response.data[0]["url"]

        await update.message.reply_photo(photo=image_url, caption="✨ Here is your generated image!")
    except Exception as e:
        logger.error(f"Text-to-Image error: {e}")
        await update.message.reply_text("❌ Failed to generate the image.")
    
    await show_menu(update, context)


# ✅ Image-to-Image Mode
async def handle_image_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles image-to-image transformation"""
    user_id = update.effective_user.id

    if user_modes.get(user_id) != "image_to_image":
        await show_menu(update, context)
        return

    if not update.message.photo:
        await update.message.reply_text("Please send an image.")
        return

    await update.message.reply_text("⏳ Uploading and transforming image...")

    # Get the highest resolution image
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Download the image
    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    image_bytes.seek(0)

    # Upload image to Cloudinary
    image_url = upload_to_cloudinary(image_bytes)
    if not image_url:
        await update.message.reply_text("❌ Failed to upload the image.")
        return

    # GPT-4o Image-to-Image
    try:
        response = client.images.edit(model="gpt-4o", image=image_url, prompt="Studio Ghibli anime style")
        transformed_url = response.data[0]["url"]

        await update.message.reply_photo(photo=transformed_url, caption="✨ Here is your Studio Ghibli-style image!")
    except Exception as e:
        logger.error(f"Image-to-Image error: {e}")
        await update.message.reply_text("❌ Failed to transform the image.")
    
    await show_menu(update, context)


# ✅ /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command to initiate the bot"""
    await update.message.reply_text("✨ Welcome to the Studio Ghibli Bot!")
    await show_menu(update, context)


# ✅ Main Function
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mode_selection))
    app.add_handler(MessageHandler(filters.TEXT, handle_chat))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image_to_image))

    logger.info("Bot started...")
    app.run_polling()


# ✅ Start the bot
if __name__ == "__main__":
    main()