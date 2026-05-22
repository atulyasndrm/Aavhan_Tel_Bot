import logging 
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_ID
from app.db.postgres import db_pool

logger = logging.getLogger(__name__)

#===== STATES =====
NAME, PHONE, DOCUMENT = range(3)



#===== START VERIFICATION =====
async def start_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user.id)
    
    if existing:
        if existing.get("verified"):
            await update.message.reply_text("✅ You are already verified.")
            return ConversationHandler.END
        
        if existing.get("verification_status") == "pending":
            await update.message.reply_text("⏳ Your verification is under review.")
            return ConversationHandler.END
        
    await update.message.reply_text("🙏 Welcome to Aavhan\n\nEnter your full name:")  
    
    return NAME



#===== STEP 1 : NAME =====
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return NAME

    context.user_data["name"] = update.message.text

    contact_btn = KeyboardButton("📱 Share Phone Number", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)

    await update.message.reply_text(
        "Please share your phone number:",
        reply_markup=markup
    )

    return PHONE


# ===== STEP 2: PHONE =====
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.contact:
        await update.message.reply_text(
            "❌ Please tap the button to share your phone number."
        )
        return PHONE

    contact = update.message.contact
    context.user_data["phone"] = contact.phone_number

    await update.message.reply_text("📄 Upload your ID proof (Aadhaar/PAN):")

    return DOCUMENT



# ===== STEP 3: DOCUMENT =====
async def get_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document and not update.message.photo:
         await update.message.reply_text("❌ Please upload a valid document.")
         return DOCUMENT
     
    file_id = (
        update.message.document.file_id
        if update.message.document
        else update.message.photo[-1].file_id
    )
     
    user = update.effective_user
    doc_type = "document" if update.message.document else "photo"
     
      # Save to DB
    data = {
        "id": user.id,
        "name": context.user_data["name"],
        "phone": context.user_data["phone"],
        "role": "priest",
        "verified": False,
        "verification_status": "pending",
        "document": file_id,
        "doc_type": doc_type,
    }
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, name, phone, role, verified, verification_status, document)
            VALUES ($1, $2, $3, 'priest', FALSE, 'pending', $4)
            ON CONFLICT (id) DO UPDATE SET 
            name = EXCLUDED.name, phone = EXCLUDED.phone, 
            verified = FALSE, verification_status = 'pending', document = EXCLUDED.document
        """, user.id, data["name"], data["phone"], data["document"])
    
    await update.message.reply_text(
        "✅ Submitted! Waiting for admin approval.",
        reply_markup=ReplyKeyboardRemove()
    )
    
     # Notify Admin
    await notify_admin(context, user.id, data)
    
    return ConversationHandler.END


# ===== ADMIN NOTIFICATION =====
async def notify_admin(context, user_id, data):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_user_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_user_{user_id}")
        ]
    ])
    
    text = f"""
            📥 New Priest Verification

             👤 Name: {data['name']}
             📱 Phone: {data['phone']}
             🆔 ID: {user_id}
            """

    if data.get("doc_type") == "photo":
        await context.bot.send_photo(
            chat_id=int(ADMIN_ID),
            photo=data["document"],
            caption=text,
            reply_markup=keyboard
        )
    else:
        await context.bot.send_document(
            chat_id=int(ADMIN_ID),
            document=data["document"],
            caption=text,
            reply_markup=keyboard
        )