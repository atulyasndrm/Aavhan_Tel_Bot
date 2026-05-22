from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from config import ADMIN_ID


async def help_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == int(ADMIN_ID):
        admin_text = (
            "<b>👑 Admin Commands:</b>\n\n"
            "/create_job - Create and broadcast a new Puja job\n"
            "/admin_jobs - Open the admin job dashboard\n"
            "/broadcast &lt;message&gt; - Send an announcement to all verified priests\n"
            "/help - Show this menu"
        )
        keyboard = [
            [KeyboardButton("/create_job"), KeyboardButton("/admin_jobs")],
            [KeyboardButton("/broadcast"), KeyboardButton("/help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode="HTML")
        
    else:
        user_text = (
            "<b>🙏 Priest Commands:</b>\n\n"
            "/jobs - List available open Aavhans\n"
            "/applied - View your confirmed bookings\n"
            "/rejected - View your rejected jobs\n"
            "/history - View your past completed jobs\n"
            "/help - Show this menu"
        )
        keyboard = [
            [KeyboardButton("/jobs"), KeyboardButton("/applied")],
            [KeyboardButton("/rejected"), KeyboardButton("/history")],
            [KeyboardButton("/help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(user_text, reply_markup=reply_markup, parse_mode="HTML")