import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_UPLOAD_PRESET = "ml_default"

client = OpenAI(api_key=OPENAI_API_KEY)

def upload_to_cloudinary(image_bytes):
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    files = {'file': image_bytes}
    data = {"upload_preset": CLOUDINARY_UPLOAD_PRESET}
    try:
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            return response.json().get("secure_url")
        else:
            return None
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        return None

async def generate_image(prompt):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return None

async def chat_with_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return "Sorry, I couldn't process your request."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text
    if "create an image" in message.lower() or "generate an image" in message.lower():
        prompt = message.replace("create an image", "").replace("generate an image", "").strip()
        if prompt:
            await update.message.reply_text("⏳ Generating image... Please wait.")
            image_url = await generate_image(prompt)
            if image_url:
                await update.message.reply_photo(photo=image_url, caption="✨ Here is your generated image!")
            else:
                await update.message.reply_text("❌ Failed to generate the image.")
        else:
            await update.message.reply_text("Please provide a prompt for the image.")
    else:
        response = await chat_with_gpt(message)
        await update.message.reply_text(response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Uploading image... Please wait.")
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    image_bytes.seek(0)
    image_url = upload_to_cloudinary(image_bytes)
    
    if image_url:
        await update.message.reply_text("✅ Image uploaded. Now describe the modification you want.")
        context.user_data['image_url'] = image_url
    else:
        await update.message.reply_text("❌ Failed to upload the image.")

async def handle_modification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'image_url' in context.user_data:
        modification = update.message.text
        image_url = context.user_data.pop('image_url')
        await update.message.reply_text("⏳ Modifying image... Please wait.")
        result = await generate_image(f"{modification} applied to {image_url}")
        if result:
            await update.message.reply_photo(photo=result, caption="✨ Modified image!")
        else:
            await update.message.reply_text("❌ Failed to modify the image.")
    else:
        await update.message.reply_text("Send an image first before requesting a modification.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Hello! Send a message or image.")))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_modification))
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()