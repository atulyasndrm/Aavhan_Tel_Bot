from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from app.db.postgres import db_pool
from config import ADMIN_ID

# Define conversation states
# Use 10-14 to ensure these states NEVER overlap with the auth.py KYC states (0-2)
(TITLE, DATE, TIME, LOCATION, SAMAGRI, FEES) = range(10, 16)

async def start_job_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(ADMIN_ID):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 Let's create a new Puja Job!\n\n"
        "Please enter the *Job Title* (e.g., Satyanarayan Katha):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['job_title'] = update.message.text
    await update.message.reply_text(
        "📅 Enter the *Date* (Format: DD Mon YYYY, e.g., 25 Dec 2024):",
        parse_mode="Markdown"
    )
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clean up the input (removes extra spaces, trailing spaces, commas, and hyphens)
    raw_text = update.message.text.strip().replace(',', ' ').replace('-', ' ')
    # ' '.join(split()) ensures that multiple spaces between words become a single space
    date_str = ' '.join(raw_text.split())
    
    try:
        # Validate date format immediately
        datetime.strptime(date_str, "%d %b %Y")
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid date format. Please use DD Mon YYYY (e.g., 25 Dec 2024):",
            parse_mode="Markdown"
        )
        return DATE
        
    context.user_data['job_date'] = date_str
    await update.message.reply_text(
        "⏰ Enter the *Time* (Format: HH:MM AM/PM, e.g., 10:30 AM):",
        parse_mode="Markdown"
    )
    return TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clean up time string (removes dots in a.m., makes it uppercase, fixes spaces)
    raw_time = update.message.text.strip().replace('.', '').upper()
    time_str = ' '.join(raw_time.split())
    
    date_str = context.user_data['job_date']
    
    try:
        # Validate time format immediately alongside the date
        dt_str = f"{date_str} {time_str}"
        job_datetime = datetime.strptime(dt_str, "%d %b %Y %I:%M %p")
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid time format. Please strictly use HH:MM AM/PM (e.g., 10:30 AM):",
            parse_mode="Markdown"
        )
        return TIME
        
    context.user_data['job_time'] = time_str
    context.user_data['job_datetime'] = job_datetime
    await update.message.reply_text(
        "📍 Enter the *Location*:",
        parse_mode="Markdown"
    )
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['job_location'] = update.message.text
    
    reply_keyboard = [["Pandit Will Bring", "Yajman Will Arrange", "To be discussed"]]
    await update.message.reply_text(
        "📦 Select or enter the *Samagri (Materials)* arrangement:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SAMAGRI

async def get_samagri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['job_samagri'] = update.message.text
    await update.message.reply_text(
        "💰 Enter the *Fees* (e.g., 2100) or 'To be discussed':",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return FEES

async def get_fees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fees = update.message.text
    data = context.user_data
    
    title = data['job_title']
    date_str = data['job_date']
    time_str = data['job_time']
    location = data['job_location']
    samagri = data['job_samagri']
    job_datetime = data['job_datetime'] # Grab the pre-validated datetime

    # Insert into Database (This will automatically trigger the broadcast!)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO bookings (title, date, time, datetime, location, samagri, fees, status) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'open')
        """, title, date_str, time_str, job_datetime, location, samagri, fees)

    # Restore admin keyboard
    keyboard = [
        [KeyboardButton("/create_job"), KeyboardButton("/admin_jobs")],
        [KeyboardButton("/broadcast"), KeyboardButton("/help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "✅ *Job Created Successfully!*\n\n"
        "The system has automatically broadcasted this job to all verified priests.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/create_job"), KeyboardButton("/admin_jobs")],
        [KeyboardButton("/broadcast"), KeyboardButton("/help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("❌ Job creation cancelled.", reply_markup=reply_markup)
    context.user_data.clear()
    return ConversationHandler.END

create_job_conv = ConversationHandler(
    entry_points=[CommandHandler("create_job", start_job_creation)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
        SAMAGRI: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_samagri)],
        FEES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fees)],
    },
    fallbacks=[CommandHandler("cancel", cancel_creation)],
)