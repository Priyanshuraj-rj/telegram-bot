import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
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
CLOUDINARY_UPLOAD_PRESET = "ml_default"  # Cloudinary upload preset

# ✅ OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

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


# ✅ Image-to-Image Transformation
async def transform_image(image_url: str) -> str:
    """Transforms image into Studio Ghibli style using GPT-4o"""
    try:
        response = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Transform this image into Studio Ghibli anime style."},
                    {"type": "input_image", "image_url": image_url}
                ]
            }]
        )
        
        # Extract the result text or image URL
        result = response.output_text
        return result
    except Exception as e:
        logger.error(f"Error during image transformation: {e}")
        return None


# ✅ Text-to-Image Generation
async def generate_image(prompt: str) -> str:
    """Generates an image from text using GPT-4o"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        logger.error(f"Error during text-to-image generation: {e}")
        return None


# ✅ Regular Chat Mode
async def chat_with_gpt(prompt: str) -> str:
    """Handles regular chat with GPT-4o"""
    try:
        response = client.chat_completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error during chat: {e}")
        return "An error occurred during chat processing."


# ✅ /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command with mode selection"""
    keyboard = [
        ["🖼️ Image-to-Image", "📝 Text-to-Image"],
        ["💬 Chat Mode"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Welcome! Choose a mode:", reply_markup=reply_markup)


# ✅ Handle Image-to-Image Transformation
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles photo messages and transforms them"""
    if not update.message.photo:
        await update.message.reply_text("Please send an image.")
        return

    await update.message.reply_text("⏳ Uploading and processing your image...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    image_bytes.seek(0)

    image_url = upload_to_cloudinary(image_bytes)
    if not image_url:
        await update.message.reply_text("❌ Failed to upload the image.")
        return

    transformed_url = await transform_image(image_url)
    
    if transformed_url:
        await update.message.reply_text(f"✨ Here is your Studio Ghibli-style image: {transformed_url}")
    else:
        await update.message.reply_text("❌ Failed to transform the image.")
    
    await ask_for_another_mode(update)


# ✅ Handle Text-to-Image Generation
async def handle_text_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text-to-image generation"""
    prompt = update.message.text

    await update.message.reply_text("⏳ Generating image...")

    image_url = await generate_image(prompt)

    if image_url:
        await update.message.reply_photo(photo=image_url, caption="✨ Here is your generated image!")
    else:
        await update.message.reply_text("❌ Failed to generate the image.")
    
    await ask_for_another_mode(update)


# ✅ Handle Regular Chat Mode
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles regular chat interaction"""
    prompt = update.message.text
    await update.message.reply_text("💬 Thinking...")

    response = await chat_with_gpt(prompt)

    await update.message.reply_text(response)
    await ask_for_another_mode(update)


# ✅ Ask for another mode or continue chat
async def ask_for_another_mode(update: Update):
    """Prompt the user to try another mode"""
    keyboard = [
        ["🖼️ Image-to-Image", "📝 Text-to-Image"],
        ["💬 Chat Mode", "❌ Exit"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("✨ Would you like to try another mode or continue chatting?", reply_markup=reply_markup)


# ✅ Main function
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📝 Text-to-Image"), lambda u, c: u.message.reply_text("Send a text prompt for image generation.")))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("💬 Chat Mode"), lambda u, c: u.message.reply_text("Chat mode activated. Send me a message.")))
    app.add_handler(MessageHandler(filters.TEXT, handle_text_to_image))
    app.add_handler(MessageHandler(filters.TEXT, handle_chat))

    logger.info("Bot started...")
    app.run_polling()

# ✅ Start the bot
if __name__ == "__main__":
    main()