import os import logging import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters from openai import OpenAI from datetime import datetime, timedelta from io import BytesIO

✅ Logger

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

✅ Environment Variables

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME") CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY") CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET") CLOUDINARY_UPLOAD_PRESET = "ml_default"

✅ OpenAI Client

client = OpenAI(api_key=OPENAI_API_KEY)

✅ User Data Storage

users = {} admin_username = "@wev999"

✅ Helper Functions

def upload_to_cloudinary(image_bytes): """Uploads image to Cloudinary and returns the URL""" url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload" files = {'file': image_bytes} data = {"upload_preset": CLOUDINARY_UPLOAD_PRESET}

response = requests.post(url, files=files, data=data)
if response.status_code == 200:
    image_url = response.json().get("secure_url")
    logger.info(f"Image uploaded: {image_url}")
    return image_url
else:
    logger.error(f"Failed to upload image: {response.text}")
    return None

def check_premium(user_id): """Check if user has premium membership""" return users.get(user_id, {}).get('premium', False)

def add_points(user_id, points=1): """Add points to user""" if user_id not in users: users[user_id] = {'points': 2, 'referrals': 0, 'premium': False} users[user_id]['points'] += points

def deduct_points(user_id, points=1): """Deduct points from user""" users[user_id]['points'] -= points

def has_sufficient_points(user_id): """Check if user has enough points or premium""" return check_premium(user_id) or users[user_id]['points'] > 0

def generate_inline_keyboard(): """Generate mode selection buttons""" keyboard = [ [InlineKeyboardButton("🖼️ Image-to-Image", callback_data="image_to_image")], [InlineKeyboardButton("📝 Text-to-Image", callback_data="text_to_image")], [InlineKeyboardButton("💬 Chat Mode", callback_data="chat_mode")], [InlineKeyboardButton("💻 Code Generator", callback_data="code_mode")], [InlineKeyboardButton("❌ Exit", callback_data="exit")] ] return InlineKeyboardMarkup(keyboard)

✅ Commands

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if user_id not in users: users[user_id] = {'points': 2, 'referrals': 0, 'premium': False} await update.message.reply_text( "👋 Welcome! You have 2 free images per day. Refer a friend to earn 1 point per referral.\n" "Use the buttons below to choose a mode.", reply_markup=generate_inline_keyboard() )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id ref_code = f"/start {user_id}" await update.message.reply_text(f"🎯 Share this referral link: {ref_code}")

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.username == admin_username[1:]: user_id = int(context.args[0]) users[user_id]['premium'] = True await update.message.reply_text(f"✅ User {user_id} has been granted premium membership.") else: await update.message.reply_text("❌ You are not authorized.")

✅ Mode Handlers

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if not has_sufficient_points(user_id): await update.message.reply_text(f"❌ You don't have enough points. Contact {admin_username} for premium.") return

photo = update.message.photo[-1]
file = await context.bot.get_file(photo.file_id)
image_bytes = BytesIO()
await file.download_to_memory(image_bytes)
image_bytes.seek(0)

image_url = upload_to_cloudinary(image_bytes)
if not image_url:
    await update.message.reply_text("❌ Failed to upload image.")
    return

deduct_points(user_id)
await update.message.reply_text(f"✅ Image uploaded: {image_url}")
await update.message.reply_text("✨ Would you like to modify this image or generate another?", reply_markup=generate_inline_keyboard())

async def chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("💬 Chat mode activated. Send me a message.")

async def text_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("📝 Send me the text prompt for the image you want to generate!")

async def code_mode(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("💻 Code generator mode activated. Send your request!")

✅ Inline Callback Handler

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() if query.data == "image_to_image": await text_to_image(query, context) elif query.data == "text_to_image": await text_to_image(query, context) elif query.data == "chat_mode": await chat_mode(query, context) elif query.data == "code_mode": await code_mode(query, context) elif query.data == "exit": await query.edit_message_text("👋 Exiting. Use /start to restart.")

✅ Main Function

def main(): app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("refer", refer))
app.add_handler(CommandHandler("add_premium", add_premium))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(CallbackQueryHandler(button_callback))

logger.info("Bot started...")
app.run_polling()

if name == "main": main()

