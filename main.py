import requests
import logging
from io import BytesIO
from PIL import Image
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Upload image to Cloudinary
def upload_to_cloudinary(image_bytes):
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    headers = {"Authorization": f"Basic {requests.auth._basic_auth_str(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)}"}
    
    files = {"file": image_bytes}
    data = {"upload_preset": "ml_default"}  # Default upload preset

    response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        image_url = response.json().get("secure_url")
        logger.info(f"Image uploaded successfully: {image_url}")
        return image_url
    else:
        logger.error(f"Failed to upload image: {response.text}")
        return None


# ✅ Convert Telegram image to bytes
async def get_image_bytes(bot: Bot, file_id: str):
    new_file = await bot.get_file(file_id)
    image_bytes = BytesIO()
    await new_file.download_to_memory(image_bytes)
    image_bytes.seek(0)
    return image_bytes


# ✅ Transform image with GPT-4o
async def transform_image(image_url: str) -> str:
    """Transforms image into Studio Ghibli style using GPT-4o Vision."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Turn this image into Studio Ghibli style."},
                        {"type": "image_url", "image_url": image_url}
                    ]
                }
            ],
            max_tokens=1000
        )

        # Extract transformed image URL
        if response and response.choices:
            transformed_image_url = response.choices[0].message.content
            return transformed_image_url
        else:
            logger.error("No response received from the API.")
            return None

    except Exception as e:
        logger.error(f"Error during image transformation: {e}")
        return None


# ✅ Handle photo messages
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photo messages."""
    photo = update.message.photo[-1]  # Get highest quality image
    image_bytes = await get_image_bytes(context.bot, photo.file_id)

    # Upload image to Cloudinary
    image_url = upload_to_cloudinary(image_bytes)
    if not image_url:
        await update.message.reply_text("Failed to upload the image.")
        return

    await update.message.reply_text("Image uploaded. Processing...")

    # Transform the image
    transformed_url = await transform_image(image_url)

    if transformed_url:
        await update.message.reply_photo(photo=transformed_url)
    else:
        await update.message.reply_text("Failed to transform the image.")


# ✅ Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    await update.message.reply_text("Send me a photo, and I'll transform it into a Studio Ghibli-style image!")


# ✅ Main bot function
def main():
    """Start the bot."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()