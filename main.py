import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import OpenAI
from io import BytesIO
from datetime import datetime, timedelta
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_UPLOAD_PRESET = "ml_default"
ADMIN_USERNAME = "@wev999"

client = OpenAI(api_key=OPENAI_API_KEY)

user_data_file = "user_data.json"

def load_user_data():
    if not os.path.exists(user_data_file):
        with open(user_data_file, "w") as f:
            json.dump({}, f)
    with open(user_data_file, "r") as f:
        return json.load(f)

def save_user_data(data):
    with open(user_data_file, "w") as f:
        json.dump(data, f)

user_data = load_user_data()

def upload_to_cloudinary(image_bytes):
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    files = {'file': image_bytes}
    data = {"upload_preset": CLOUDINARY_UPLOAD_PRESET}
    try:
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            return response.json().get("secure_url")
        return None
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        return None

async def generate_image(prompt, image_url=None):
    try:
        content = [{"type": "text", "text": prompt}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        response = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
        return response.data[0].url
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return None

async def generate_code(prompt):
    try:
        response = client.completions.create(model="gpt-4o", prompt=prompt, max_tokens=1024)
        return response.choices[0].text
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        return None

async def chat_with_gpt(prompt):
    try:
        response = client.completions.create(model="gpt-4o", prompt=prompt, max_tokens=1024)
        return response.choices[0].text
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return None

def update_user_points(user_id, points):
    if user_id not in user_data:
        user_data[user_id] = {"points": 2, "last_free_reset": str(datetime.utcnow()), "is_premium": False, "referrals": []}
    user_data[user_id]["points"] += points
    save_user_data(user_data)

def deduct_user_points(user_id):
    if user_id in user_data:
        user_data[user_id]["points"] -= 1
        save_user_data(user_data)

def check_free_daily_reset(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"points": 2, "last_free_reset": str(datetime.utcnow()), "is_premium": False, "referrals": []}
    last_reset = datetime.fromisoformat(user_data[user_id]["last_free_reset"])
    if datetime.utcnow() - last_reset > timedelta(days=1):
        user_data[user_id]["points"] = 2
        user_data[user_id]["last_free_reset"] = str(datetime.utcnow())
        save_user_data(user_data)

def has_premium(user_id):
    return user_data.get(user_id, {}).get("is_premium", False)

def has_enough_points(user_id):
    return user_data.get(user_id, {}).get("points", 0) > 0 or has_premium(user_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    check_free_daily_reset(user_id)
    await update.message.reply_text("🎉 Welcome! Choose a mode:", reply_markup=mode_buttons())

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) == 1:
        referrer_id = context.args[0]
        if referrer_id != user_id and referrer_id in user_data and user_id not in user_data[referrer_id]["referrals"]:
            user_data[referrer_id]["referrals"].append(user_id)
            update_user_points(referrer_id, 1)
            await update.message.reply_text(f"✅ You have been referred by {referrer_id}.")
        else:
            await update.message.reply_text("❌ Invalid or duplicate referral.")
    else:
        await update.message.reply_text(f"🔗 Share this link: `https://t.me/{context.bot.username}?start={user_id}`")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    check_free_daily_reset(user_id)
    if not has_enough_points(user_id):
        await update.message.reply_text(f"❌ You need more points. Contact admin {ADMIN_USERNAME} to buy membership.")
        return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    image_bytes.seek(0)
    image_url = upload_to_cloudinary(image_bytes)
    if image_url:
        deduct_user_points(user_id)
        await update.message.reply_text("🔥 Send me your modification prompt!")
        context.user_data["image_url"] = image_url
    else:
        await update.message.reply_text("❌ Failed to upload image.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if "image_url" in context.user_data:
        image_url = context.user_data.pop("image_url")
        await update.message.reply_text("⏳ Generating modified image...")
        result = await generate_image(update.message.text, image_url)
        if result:
            await update.message.reply_photo(result, caption="✅ Modified image.")
        else:
            await update.message.reply_text("❌ Failed to modify image.")
    else:
        result = await chat_with_gpt(update.message.text)
        await update.message.reply_text(result or "❌ Failed to respond.")

async def text_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    check_free_daily_reset(user_id)
    if not has_enough_points(user_id):
        await update.message.reply_text(f"❌ You need more points. Contact admin {ADMIN_USERNAME}.")
        return
    prompt = " ".join(context.args)
    await update.message.reply_text("⏳ Generating image...")
    result = await generate_image(prompt)
    if result:
        deduct_user_points(user_id)
        await update.message.reply_photo(result, caption="✅ Here is your image.")
    else:
        await update.message.reply_text("❌ Failed to generate image.")

async def code_generator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💻 Send me the prompt for the code.")
    context.user_data["mode"] = "code"

async def handle_code_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await generate_code(update.message.text)
    await update.message.reply_text(f"🛠️ Code: \n```\n{result or '❌ Failed to generate code.'}\n```", parse_mode="Markdown")

async def admin_add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username == ADMIN_USERNAME.lstrip("@"):
        user_id = context.args[0]
        if user_id in user_data:
            user_data[user_id]["is_premium"] = True
            save_user_data(user_data)
            await update.message.reply_text(f"✅ User {user_id} now has premium access.")
        else:
            await update.message.reply_text("❌ Invalid user ID.")

def mode_buttons():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🖼️ Image Mode", callback_data="image")], [InlineKeyboardButton("💬 Chat Mode", callback_data="chat")], [InlineKeyboardButton("💻 Code Mode", callback_data="code")]])

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("refer", refer))
    app.run_polling()

if __name__ == "__main__":
    main()