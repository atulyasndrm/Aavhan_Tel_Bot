from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from config import ADMIN_ID


async def help_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == int(ADMIN_ID):
        admin_text = (
            "<b>👑 Admin Commands:</b>\n\n"
            "➕ <b>Create Job</b> - Create and broadcast a new Puja job\n"
            "📋 <b>Admin Jobs</b> - Open the admin job dashboard\n"
            "📢 <b>Broadcast</b> - Send an announcement to all verified priests\n"
            "🔍 <b>Find Priest</b> - Search for a priest by name/phone/id\n"
            "/help - Show this menu"
        )
        keyboard = [
            [KeyboardButton("➕ Create Job"), KeyboardButton("📋 Admin Jobs")],
            [KeyboardButton("📢 Broadcast"), KeyboardButton("🔍 Find Priest")],
            [KeyboardButton("/help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode="HTML")
        
    else:
        user_text = (
            "<b>🙏 Priest Commands:</b>\n\n"
            "📿 <b>Open Jobs</b> - List available open Aavhans\n"
            "✅ <b>Applied</b> - View your confirmed bookings\n"
            "❌ <b>Rejected</b> - View your rejected jobs\n"
            "📜 <b>History</b> - View your past completed jobs\n"
            "✏️ <b>Edit Profile</b> - Update your phone number or ID\n"
            "/help - Show this menu"
        )
        keyboard = [
            [KeyboardButton("📿 Open Jobs"), KeyboardButton("✅ Applied")],
            [KeyboardButton("❌ Rejected"), KeyboardButton("📜 History")],
            [KeyboardButton("✏️ Edit Profile"), KeyboardButton("/help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(user_text, reply_markup=reply_markup, parse_mode="HTML")