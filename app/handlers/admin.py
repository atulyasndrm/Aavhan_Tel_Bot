from telegram import Update
from telegram.ext import ContextTypes

from app.db.postgres import db_pool
from config import ADMIN_ID

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
            await conn.execute("UPDATE users SET verified = TRUE, verification_status = 'approved' WHERE id = $1", user_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 You are VERIFIED! You can now use the bot."
            )
        except Exception as e:
            print("Send error:", e)

        await edit_admin_reply("✅ Approved")

    # ===== REJECT USER =====
    elif data.startswith("reject_user_"):
        user_id = int(data.split("_")[2])

        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET verified = FALSE, verification_status = 'rejected' WHERE id = $1", user_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Your verification was rejected."
            )
        except Exception as e:
            print("Send error:", e)

        await edit_admin_reply("❌ Rejected")


# ===== ADMIN BROADCAST =====
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id != int(ADMIN_ID):
        await update.message.reply_text("⛔ Access denied.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ *Usage:* `/broadcast <your message here>`", parse_mode="Markdown")
        return

    message_text = " ".join(context.args)
    full_message = f"📢 *Admin Announcement*\n\n{message_text}"

    async with db_pool.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users WHERE verified = TRUE")
        
    sent_count = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=user["id"], text=full_message, parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            print(f"Broadcast error for {user['id']}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent successfully to {sent_count} verified priests.")