import os
import logging
import requests
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from io import BytesIO

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_UPLOAD_PRESET = "ml_default"  # Your Cloudinary preset name

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Cloudinary Upload Function
def upload_to_cloudinary(image_bytes):
    """Uploads image to Cloudinary and returns the URL"""
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    
    files = {'file': image_bytes}
    data = {
        "upload_preset": CLOUDINARY_UPLOAD_PRESET
    }

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


# ✅ Transform Image to Studio Ghibli Style
async def transform_image(image_url: str) -> str:
    """Transforms image into Studio Ghibli style"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt="Transform this photo into Studio Ghibli anime style",
            image={"url": image_url},
            style="anime"
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"Error during image transformation: {e}")
        return None


# ✅ /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Send me a photo, and I'll transform it into a Studio Ghibli-style image!")

# ✅ Handle image messages
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles photo messages and transforms them"""
    if not update.message.photo:
        await update.message.reply_text("Please send an image.")
        return

    # Notify user: Processing...
    await update.message.reply_text("⏳ Processing your image...")

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

    # Transform image
    transformed_url = await transform_image(image_url)
    if transformed_url:
        await update.message.reply_photo(photo=transformed_url, caption="✨ Here is your Studio Ghibli-style image!")
    else:
        await update.message.reply_text("❌ Failed to transform the image.")

# ✅ Main function
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    logger.info("Bot started...")
    app.run_polling()

# ✅ Start the bot
if __name__ == "__main__":
    main()