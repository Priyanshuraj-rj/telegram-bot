import os
import logging
import requests
from telegram import Update
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

# ✅ User state management
user_states = {}

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


# ✅ Transform Image with GPT-4o
async def transform_image(image_url: str, prompt: str) -> str:
    """Transforms image using GPT-4o with a provided prompt"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
            image_url=image_url
        )

        image_url = response.data[0].url
        return image_url
    except Exception as e:
        logger.error(f"Error during image transformation: {e}")
        return None


# ✅ Generate Image from Text with GPT-4o
async def generate_image_from_text(prompt: str) -> str:
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
        logger.error(f"Error during image generation: {e}")
        return None


# ✅ /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message with mode selection"""
    await update.message.reply_text(
        "Welcome! 🌟 Choose an option:\n"
        "1️⃣ /text_to_image - Generate an image from text\n"
        "2️⃣ /image_to_image - Transform an existing image"
    )


# ✅ /text_to_image command
async def text_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sets the bot to text-to-image mode"""
    user_states[update.effective_chat.id] = 'text_to_image'
    await update.message.reply_text("Send me the text prompt for the image you want to generate!")


# ✅ /image_to_image command
async def image_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sets the bot to image-to-image mode"""
    user_states[update.effective_chat.id] = 'image_to_image'
    await update.message.reply_text("Send me the image you want to transform.")


# ✅ Handle text prompts for image generation
async def handle_text_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text prompts for text-to-image generation"""
    if update.effective_chat.id not in user_states or user_states[update.effective_chat.id] != 'text_to_image':
        return

    prompt = update.message.text
    await update.message.reply_text("⏳ Generating image... Please wait.")

    image_url = await generate_image_from_text(prompt)

    if image_url:
        await update.message.reply_photo(image_url, caption="✨ Here is your generated image!")
    else:
        await update.message.reply_text("❌ Failed to generate the image.")

    del user_states[update.effective_chat.id]


# ✅ Handle image uploads
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles photo messages and processes them"""
    if update.effective_chat.id not in user_states:
        await update.message.reply_text("Please select /image_to_image or /text_to_image first.")
        return

    mode = user_states[update.effective_chat.id]

    # Download the image
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    image_bytes.seek(0)

    # Upload to Cloudinary
    image_url = upload_to_cloudinary(image_bytes)

    if not image_url:
        await update.message.reply_text("❌ Failed to upload the image.")
        return

    if mode == 'image_to_image':
        await update.message.reply_text("✅ Image uploaded! Now, send me the text prompt for the transformation.")
        user_states[update.effective_chat.id] = {'mode': 'image_to_image', 'image_url': image_url}
    else:
        await update.message.reply_text("❌ Please use /image_to_image before sending an image.")


# ✅ Handle image transformation prompts
async def handle_transformation_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles transformation prompts after image upload"""
    chat_id = update.effective_chat.id

    if chat_id not in user_states or not isinstance(user_states[chat_id], dict):
        await update.message.reply_text("❌ Please upload an image first.")
        return

    data = user_states[chat_id]
    image_url = data['image_url']
    prompt = update.message.text

    await update.message.reply_text("⏳ Transforming image... Please wait.")

    # Perform the image transformation
    transformed_image_url = await transform_image(image_url, prompt)

    if transformed_image_url:
        await update.message.reply_photo(transformed_image_url, caption="✨ Here is your transformed image!")
    else:
        await update.message.reply_text("❌ Failed to transform the image.")

    del user_states[chat_id]


# ✅ Main function
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("text_to_image", text_to_image))
    app.add_handler(CommandHandler("image_to_image", image_to_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_prompt))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transformation_prompt))

    logger.info("Bot started...")
    app.run_polling()


# ✅ Start the bot
if __name__ == "__main__":
    main()