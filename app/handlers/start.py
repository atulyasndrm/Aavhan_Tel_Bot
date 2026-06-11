from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from app.db.postgres import db_pool
from app.handlers.auth import start_verification
from config import ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Auto-verify the admin so they immediately get access to the menu
    if user.id == int(ADMIN_ID):
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, name, role, verification_status, verified)
                VALUES ($1, $2, 'admin', 'approved', TRUE)
                ON CONFLICT (id) DO UPDATE SET 
                verified = TRUE, verification_status = 'approved', role = 'admin', name = EXCLUDED.name
            """, str(user.id), user.full_name)

    async with db_pool.acquire() as conn:
        db_user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user.id))
    
    if not db_user:
        return await start_verification(update, context)
    
    if not db_user.get("verified"):
        status = db_user.get("verification_status")
        
        if status == "pending":
            await update.message.reply_text("⏳ Your verification is in progress.")
        
        elif status == "rejected":
            await update.message.reply_text("❌ Verification rejected. Contact admin.")
            return ConversationHandler.END
        else:
            return await start_verification(update, context)
            
        return ConversationHandler.END
    
    # Build the main menu keyboard
    if user.id == int(ADMIN_ID):
        keyboard = [
            [KeyboardButton("➕ Create Job"), KeyboardButton("📋 Admin Jobs")],
            [KeyboardButton("📢 Broadcast"), KeyboardButton("🔍 Find Priest")],
            [KeyboardButton("/help")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📿 Open Jobs"), KeyboardButton("✅ Applied")],
            [KeyboardButton("❌ Rejected"), KeyboardButton("🎉 Completed Jobs")],
            [KeyboardButton("🪪 My Portfolio"), KeyboardButton("📥 Download PDF")],
            [KeyboardButton("✏️ Edit Profile"), KeyboardButton("/help")]
        ]
        
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🙏 Welcome back! You are verified.\n\nChoose an option from the menu below:", 
        reply_markup=reply_markup
    )

    return ConversationHandler.END