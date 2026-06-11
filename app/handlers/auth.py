import logging 
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler

from config import ADMIN_ID
from app.db.postgres import db_pool

logger = logging.getLogger(__name__)

#===== STATES =====
NAME, PHONE, DOCUMENT, CONFIRM = range(4)



#===== START VERIFICATION =====
async def start_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user.id))
    
    if existing:
        if existing.get("verified"):
            await update.message.reply_text("✅ You are already verified.")
            return ConversationHandler.END
        
        if existing.get("verification_status") == "pending":
            await update.message.reply_text("⏳ Your verification is under review.")
            return ConversationHandler.END
        
    await update.message.reply_text("🙏 Welcome to Aavhan\n\nEnter your full name:")  
    
    return NAME


#===== EDIT PROFILE =====
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user.id))
    
    if not existing:
        await update.message.reply_text("❌ You are not registered yet. Please type /verify to start.")
        return ConversationHandler.END
        
    # Pre-fill user data from the database
    context.user_data["name"] = existing.get("name", "")
    context.user_data["phone"] = existing.get("phone", "")
    context.user_data["document"] = existing.get("document", "")
    context.user_data["doc_type"] = existing.get("doc_type", "document")
    
    await update.message.reply_text(
        "⚠️ *Note:* Editing your profile will temporarily suspend your verified status and resubmit it for Admin approval.",
        parse_mode="Markdown"
    )
    
    return await show_confirmation(update, context)


#===== MY PORTFOLIO =====
async def send_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    async with db_pool.acquire() as conn:
        db_user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user.id))
        
        if not db_user or not db_user.get("verified"):
            await update.message.reply_text("⛔ You must be a verified priest to view your portfolio.")
            return
            
        completed_count = await conn.fetchval("""
            SELECT COUNT(*) FROM bookings 
            WHERE assigned_priest = $1 AND status = 'completed'
        """, user.id)
        
    from app.services.image_service import generate_portfolio_card
    image_bytes = generate_portfolio_card(db_user, completed_count)
    
    await update.message.reply_photo(
        photo=image_bytes,
        caption=(
            "🪪 *Your Verified Digital Business Card*\n\n"
            "You can forward this image to your private Yajmans (hosts) "
            "on WhatsApp or Telegram to showcase your verified experience and build trust!"
        ),
        parse_mode="Markdown"
    )


#===== STEP 1 : NAME =====
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return NAME

    name = update.message.text.strip()
    if len(name) < 3 or len(name) > 50:
        await update.message.reply_text("⚠️ Please enter a valid full name (3-50 characters):")
        return NAME

    context.user_data["name"] = name

    if context.user_data.get("edit_mode"):
        return await show_confirmation(update, context)

    contact_btn = KeyboardButton("📱 Share Phone Number", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)

    await update.message.reply_text(
        "Please share your phone number using the button below, or type it manually:",
        reply_markup=markup
    )

    return PHONE


# ===== STEP 2: PHONE =====
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_text = ""
    if update.message.contact:
        contact = update.message.contact
        
        # Production Security Check: Ensure the shared contact actually belongs to the active user
        if contact.user_id != update.effective_user.id:
            await update.message.reply_text(
                "❌ For security reasons, you must share your *OWN* Telegram contact using the button provided. If it's failing, please type your number manually.",
                parse_mode="Markdown"
            )
            return PHONE
            
        phone_text = contact.phone_number
    elif update.message.text:
        phone_text = update.message.text.strip()
        
        if any(char.isalpha() for char in phone_text):
            await update.message.reply_text("⚠️ Please enter numbers only, not words. (e.g., 9876543210)")
            return PHONE
            
    else:
        await update.message.reply_text("❌ Please tap the button to share your contact or type your phone number manually.")
        return PHONE
        
    # Clean and validate the extracted phone number (from either contact or text)
    digits_only = ''.join(filter(str.isdigit, phone_text))
    
    # Handle country code (+91) or leading zero
    if len(digits_only) == 12 and digits_only.startswith('91'):
        digits_only = digits_only[2:]
    elif len(digits_only) == 11 and digits_only.startswith('0'):
        digits_only = digits_only[1:]

    # Validate exact 10 digits and Indian mobile prefix (6-9)
    if len(digits_only) != 10 or digits_only[0] not in "6789":
        await update.message.reply_text("⚠️ Please provide a valid 10-digit Indian phone number.")
        return PHONE
        
    context.user_data["phone"] = "+91" + digits_only

    if context.user_data.get("edit_mode"):
        return await show_confirmation(update, context)

    # Remove the contact button from the screen
    await update.message.reply_text("📄 Upload your ID proof (Aadhaar/PAN):", reply_markup=ReplyKeyboardRemove())

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
     
    context.user_data["document"] = file_id
    context.user_data["doc_type"] = doc_type

    return await show_confirmation(update, context)

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("name", "N/A")
    phone = context.user_data.get("phone", "N/A")
    doc_type = context.user_data.get("doc_type", "document")
    
    summary = (
        "📋 *Please Confirm Your Details*\n\n"
        f"👤 *Name:* {name}\n"
        f"📱 *Phone:* {phone}\n"
        f"📄 *Document:* Uploaded ({doc_type})\n\n"
        "Is everything correct?"
    )
    
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("✅ Confirm & Submit")],
        [KeyboardButton("✏️ Edit Name"), KeyboardButton("📱 Edit Phone")],
        [KeyboardButton("📄 Edit Document"), KeyboardButton("❌ Cancel")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=keyboard)
    return CONFIRM


# ===== STEP 4: CONFIRM =====
async def confirm_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "❌ Cancel":
        return await cancel_auth(update, context)
        
    if text == "✏️ Edit Name":
        context.user_data["edit_mode"] = True
        await update.message.reply_text("Enter your full name:", reply_markup=ReplyKeyboardRemove())
        return NAME
        
    if text == "📱 Edit Phone":
        context.user_data["edit_mode"] = True
        contact_btn = KeyboardButton("📱 Share Phone Number", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
        await update.message.reply_text("Please share your phone number or type it manually:", reply_markup=markup)
        return PHONE
        
    if text == "📄 Edit Document":
        context.user_data["edit_mode"] = True
        await update.message.reply_text("📄 Upload your ID proof (Aadhaar/PAN):", reply_markup=ReplyKeyboardRemove())
        return DOCUMENT

    if text != "✅ Confirm & Submit":
        await update.message.reply_text("⚠️ Please use the buttons below to confirm or edit.")
        return CONFIRM
        
    user = update.effective_user
    
    data = {
        "id": user.id,
        "name": context.user_data["name"],
        "phone": context.user_data["phone"],
        "role": "priest",
        "verified": False,
        "verification_status": "pending",
        "document": context.user_data["document"],
        "doc_type": context.user_data["doc_type"],
    }
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, name, phone, role, verified, verification_status, document, doc_type, created_at, updated_at)
            VALUES ($1, $2, $3, 'priest', FALSE, 'pending', $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET 
            name = EXCLUDED.name, phone = EXCLUDED.phone, 
            verified = FALSE, verification_status = 'pending', document = EXCLUDED.document,
            doc_type = EXCLUDED.doc_type,
            updated_at = CURRENT_TIMESTAMP
        """, str(user.id), data["name"], data["phone"], data["document"], data["doc_type"])
    
    await update.message.reply_text(
        "✅ Submitted! Waiting for admin approval.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Notify Admin
    await notify_admin(context, user.id, data)
    
    context.user_data.clear()
    return ConversationHandler.END


# ===== CANCEL VERIFICATION =====
async def cancel_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user.id))
        
    context.user_data.clear()
    
    if user.id == int(ADMIN_ID):
        keyboard = [
            [KeyboardButton("➕ Create Job"), KeyboardButton("📋 Admin Jobs")],
            [KeyboardButton("📢 Broadcast"), KeyboardButton("🔍 Find Priest")],
            [KeyboardButton("/help")]
        ]
        await update.message.reply_text(
            "❌ Action cancelled.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    elif existing and existing.get("verified"):
        keyboard = [
            [KeyboardButton("📿 Open Jobs"), KeyboardButton("✅ Applied")],
            [KeyboardButton("❌ Rejected"), KeyboardButton("🎉 Completed Jobs")],
            [KeyboardButton("🪪 My Portfolio"), KeyboardButton("📥 Download PDF")],
            [KeyboardButton("✏️ Edit Profile"), KeyboardButton("/help")]
        ]
        await update.message.reply_text(
            "❌ Profile edit cancelled. Your profile remains unchanged.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "❌ Verification cancelled. You can type /verify later to try again.",
            reply_markup=ReplyKeyboardRemove()
        )
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