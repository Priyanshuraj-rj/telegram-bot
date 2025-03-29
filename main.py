import os
import logging
from io import BytesIO
from PIL import Image
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve API keys from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY

async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome! Send me a photo, and I'll transform it into a Studio Ghibli-style image."
    )

async def handle_photo(update: Update, context: CallbackContext) -> None:
    """Handle incoming photos from users."""
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_stream = BytesIO()
    await file.download_to_memory(image_stream)
    image_stream.seek(0)

    # Process the image
    transformed_image_stream = await transform_image(image_stream)

    if transformed_image_stream:
        # Send the transformed image back to the user
        transformed_image_stream.seek(0)
        await update.message.reply_photo(photo=transformed_image_stream)
    else:
        await update.message.reply_text("Sorry, I couldn't process the image.")

async def transform_image(image_stream: BytesIO) -> BytesIO:
    """Transform the image using OpenAI's API to achieve a Studio Ghibli style."""
    try:
        # Prepare the image for OpenAI API
        image = Image.open(image_stream)
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        buffered.seek(0)

        # Call OpenAI API for image transformation
        response = openai.Image.create_variation(
            image=buffered,
            n=1,
            size="1024x1024"
        )

        # Retrieve the transformed image URL
        transformed_image_url = response['data'][0]['url']

        # Download the transformed image
        transformed_image_response = requests.get(transformed_image_url)
        transformed_image_stream = BytesIO(transformed_image_response.content)

        return transformed_image_stream

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