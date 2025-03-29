import os
import logging
from io import BytesIO
from PIL import Image
import base64
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from openai import OpenAI

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: CallbackContext) -> None:
    """Welcome message"""
    await update.message.reply_text("Send me a photo, and I'll transform it into a Studio Ghibli-style image!")

async def handle_photo(update: Update, context: CallbackContext) -> None:
    """Handles photos sent by the user."""
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_stream = BytesIO()
    await file.download_to_memory(image_stream)
    image_stream.seek(0)

    # Convert image to Base64
    image_b64 = base64.b64encode(image_stream.getvalue()).decode('utf-8')
    
    # Process the image
    transformed_image_url = await transform_image(image_b64)

    if transformed_image_url:
        await update.message.reply_photo(photo=transformed_image_url)
    else:
        await update.message.reply_text("Failed to transform the image.")

async def transform_image(image_b64: str) -> str:
    """Transforms the image using GPT-4o image processing."""
    try:
        response = client.responses.create(
            model="gpt-4o",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Transform this into Studio Ghibli style"},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{image_b64}",
                            "detail": "high"
                        }
                    ]
                }
            ]
        )

        # Get the transformed image URL
        transformed_image_url = response.output_text  # URL of the processed image
        return transformed_image_url

    except Exception as e:
        logger.error(f"Error during image transformation: {e}")
        return None

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()