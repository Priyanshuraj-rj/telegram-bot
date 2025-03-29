import logging
import base64
import os
from io import BytesIO
from PIL import Image
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import asyncio

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler."""
    await update.message.reply_text("Send me a photo, and I'll transform it into a Studio Ghibli-style image!")

# Convert image to Base64
def image_to_base64(image: Image) -> str:
    """Converts PIL Image to Base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

# Transform image using OpenAI Vision API
async def transform_image(image_b64: str) -> str:
    """Transforms the image into Studio Ghibli style using GPT-4o Vision."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Turn this image into Studio Ghibli style."},
                        {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"}
                    ]
                }
            ],
            max_tokens=1000
        )

        # Extract response
        if response and response.choices:
            transformed_image_url = response.choices[0].message.content
            return transformed_image_url
        else:
            return None

    except Exception as e:
        logger.error(f"Error during image transformation: {e}")
        return None

# Loading animation
async def show_loading_animation(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Displays a loading animation while processing."""
    animation = ["⏳", "🔄", "⌛", "🔃"]
    message = await context.bot.send_message(chat_id, "Processing your image... ⏳")

    try:
        for i in range(10):  # Display animation for approx. 10 seconds
            await asyncio.sleep(1)
            await message.edit_text(f"Processing your image... {animation[i % len(animation)]}")
    except Exception as e:
        logger.warning(f"Failed to update animation message: {e}")

# Handle received image
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles image uploads and sends back the transformed image."""
    chat_id = update.message.chat_id

    # Start loading animation
    loading_task = asyncio.create_task(show_loading_animation(chat_id, context))

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download image
        image_data = BytesIO()
        await file.download_to_memory(out=image_data)

        # Open the image and convert to Base64
        image = Image.open(image_data)
        image_b64 = image_to_base64(image)

        # Transform the image
        transformed_image_url = await transform_image(image_b64)

        if transformed_image_url:
            await context.bot.send_photo(chat_id, transformed_image_url)
        else:
            await update.message.reply_text("Failed to transform the image.")

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text("Sorry, I couldn't process the image.")
    
    finally:
        loading_task.cancel()  # Stop the animation

# Main entry point
def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    logger.info("Bot started...")
    app.run_polling()