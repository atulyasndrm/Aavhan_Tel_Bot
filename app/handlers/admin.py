from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from app.db.postgres import db_pool
from config import is_admin, logger
from app.services import user_service

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    async def edit_admin_reply(status_text):
        original_text = query.message.caption if query.message.caption else query.message.text
        if query.message.document or query.message.photo:
            await query.edit_message_caption(caption=f"{original_text}\n\n{status_text}")
        else:
            await query.edit_message_text(text=f"{original_text}\n\n{status_text}")

    # ===== APPROVE USER =====
    if data.startswith("approve_user_"):
        user_id = int(data.split("_")[2])

        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET verified = TRUE, verification_status = 'approved' WHERE id = $1", str(user_id))

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 You are VERIFIED! You can now use the bot."
            )
        except Exception as e:
            logger.exception("Error sending verification approved message to user %s", user_id)

        await edit_admin_reply("✅ Approved")

    # ===== REJECT USER (Show Reasons Sub-menu) =====
    elif data.startswith("reject_user_"):
        user_id = int(data.split("_")[2])
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Reason: Blurry/Invalid ID", callback_data=f"reject_reason_{user_id}_blurry")],
            [InlineKeyboardButton("Reason: Name mismatch", callback_data=f"reject_reason_{user_id}_name")],
            [InlineKeyboardButton("Reason: Other/Invalid", callback_data=f"reject_reason_{user_id}_other")],
            [InlineKeyboardButton("⬅️ Cancel & Go Back", callback_data=f"cancel_reject_{user_id}")]
        ])
        await query.edit_message_reply_markup(reply_markup=keyboard)

    # ===== CANCEL REJECT (Back to main menu) =====
    elif data.startswith("cancel_reject_"):
        user_id = int(data.split("_")[2])
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_user_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_user_{user_id}")
            ]
        ])
        await query.edit_message_reply_markup(reply_markup=keyboard)

    # ===== EXECUTE REJECTION WITH REASON =====
    elif data.startswith("reject_reason_"):
        parts = data.split("_")
        user_id = int(parts[2])
        reason_code = parts[3]
        
        reasons = {
            "blurry": "ID document was blurry or unreadable. Please upload a clear photo/scan.",
            "name": "The name on your profile does not match the provided ID.",
            "other": "Your application did not meet the verification requirements."
        }
        reason_text = reasons.get(reason_code, "Invalid details provided.")

        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET verified = FALSE, verification_status = 'rejected' WHERE id = $1", str(user_id))

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Your verification was rejected.\n\n*Reason:* {reason_text}\n\nYou can type /verify to try again.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception("Error sending verification rejected message to user %s", user_id)

        await edit_admin_reply(f"❌ Rejected\nReason: {reason_text}")


# ===== ADMIN BROADCAST =====
BROADCAST_MESSAGE = 30

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    if context.args:
        message_text = " ".join(context.args)
        await _execute_broadcast(update, context, message_text)
        return ConversationHandler.END

    await update.message.reply_text(
        "📢 *Send Broadcast*\n\nPlease type the message you want to announce to all verified priests:",
        parse_mode="Markdown"
    )
    return BROADCAST_MESSAGE

async def broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()
    await _execute_broadcast(update, context, message_text)
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Broadcast cancelled.")
    return ConversationHandler.END

async def _execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    full_message = f"📢 *Admin Announcement*\n\n{message_text}"

    async with db_pool.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users WHERE verified = TRUE")
        
    sent_count = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=int(user["id"]), text=full_message, parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            logger.exception("Broadcast error for user %s", user['id'])

    await update.message.reply_text(f"✅ Broadcast sent successfully to {sent_count} verified priests.")


# ===== SEARCH PRIESTS =====
SEARCH_QUERY = 20

async def find_priest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    if context.args:
        query_str = " ".join(context.args)
        await _send_priest_search_results(update.message.reply_text, query_str, 0)
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 *Find Priest*\n\nPlease type the name, phone number, or Telegram ID of the priest:",
        parse_mode="Markdown"
    )
    return SEARCH_QUERY

async def find_priest_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_str = update.message.text.strip()
    await _send_priest_search_results(update.message.reply_text, query_str, 0)
    return ConversationHandler.END

async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Search cancelled.")
    return ConversationHandler.END


async def find_priest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Access denied.")
        return

    data = query.data
    parts = data.split("_", 3)
    action = parts[0]

    if action == "spr":
        offset = int(parts[1])
        query_str = parts[2]
        await _send_priest_search_results(query.edit_message_text, query_str, offset)
        
    elif action == "sa":
        user_id = int(parts[1])
        offset = int(parts[2])
        query_str = parts[3]
        
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET verified = TRUE, verification_status = 'approved' WHERE id = $1", str(user_id))

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 You are VERIFIED! You can now use the bot."
            )
        except Exception:
            logger.exception("Error sending verification approved message to user %s", user_id)
            
        await _send_priest_search_results(query.edit_message_text, query_str, offset)
        
    elif action == "sr":
        user_id = int(parts[1])
        offset = int(parts[2])
        query_str = parts[3]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Reason: Blurry/Invalid ID", callback_data=f"srr_{user_id}_{offset}_blurry_{query_str[:20]}")],
            [InlineKeyboardButton("Reason: Name mismatch", callback_data=f"srr_{user_id}_{offset}_name_{query_str[:20]}")],
            [InlineKeyboardButton("Reason: Other/Invalid", callback_data=f"srr_{user_id}_{offset}_other_{query_str[:20]}")],
            [InlineKeyboardButton("⬅️ Cancel & Go Back", callback_data=f"spr_{offset}_{query_str[:30]}")]
        ])
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif action == "srr":
        parts = data.split("_", 4)
        user_id = int(parts[1])
        offset = int(parts[2])
        reason_code = parts[3]
        query_str = parts[4]
        
        reasons = {
            "blurry": "ID document was blurry or unreadable. Please upload a clear photo/scan.",
            "name": "The name on your profile does not match the provided ID.",
            "other": "Your application did not meet the verification requirements."
        }
        reason_text = reasons.get(reason_code, "Invalid details provided.")

        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET verified = FALSE, verification_status = 'rejected' WHERE id = $1", str(user_id))

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Your verification was rejected.\n\n*Reason:* {reason_text}\n\nYou can type /verify to try again.",
                parse_mode="Markdown"
            )
        except Exception:
            logger.exception("Error sending verification rejected message to user %s", user_id)
            
        await _send_priest_search_results(query.edit_message_text, query_str, offset)


async def _send_priest_search_results(send_func, query_str: str, offset: int):
    users = await user_service.search_priests(query_str, limit=6, offset=offset)
    
    if not users and offset == 0:
        await send_func(f"📭 No priests found matching `{query_str}`.", parse_mode="Markdown")
        return
    elif not users:
        await send_func(f"📭 No more priests found matching `{query_str}`.", parse_mode="Markdown")
        return

    users_to_show = users[:5]
    more_available = len(users) > 5

    safe_query = str(query_str).replace('*', '').replace('_', '').replace('`', '')
    text = f"🔍 *Search Results for* `{safe_query}`\nPage {offset // 5 + 1}\n\n"
    keyboard = []
    
    for u in users_to_show:
        safe_name = str(u.get('name', 'Unknown')).replace('*', '').replace('_', '').replace('`', '')
        status_emoji = "✅" if u.get("verified") else ("⏳" if u.get("verification_status") == "pending" else "❌")
        text += (
            f"{status_emoji} *{safe_name}*\n"
            f"📞 {u.get('phone', 'N/A')}\n"
            f"🆔 `{u.get('id')}`\n"
            f"📌 Status: {u.get('verification_status', 'N/A').capitalize()}\n"
            f"📅 Joined: {u.get('created_at').strftime('%Y-%m-%d') if u.get('created_at') else 'N/A'}\n"
            "───────────────\n"
        )
        
        name_short = u.get("name", "Priest")[:10]
        if not u.get("verified"):
            if u.get("verification_status") == "rejected":
                keyboard.append([
                    InlineKeyboardButton(f"✅ Approve {name_short}", callback_data=f"sa_{u['id']}_{offset}_{query_str[:25]}")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(f"✅ Approve {name_short}", callback_data=f"sa_{u['id']}_{offset}_{query_str[:25]}"),
                    InlineKeyboardButton(f"❌ Reject {name_short}", callback_data=f"sr_{u['id']}_{offset}_{query_str[:25]}")
                ])

    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"spr_{offset - 5}_{query_str[:40]}"))
    if more_available:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"spr_{offset + 5}_{query_str[:40]}"))
    
    if nav_row:
        keyboard.append(nav_row)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await send_func(text, reply_markup=reply_markup, parse_mode="Markdown")