from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes

from config import ADMIN_ID
from app.services import job_service, user_service
from app.services.image_service import generate_job_image


async def admin_jobs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the admin job management menu."""
    if not update.message or update.effective_user.id != int(ADMIN_ID):
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Booked Jobs", callback_data="admin_jobs_booked")],
        [InlineKeyboardButton("❌ Rejected Jobs", callback_data="admin_jobs_rejected")],
        [InlineKeyboardButton("📬 Open Jobs", callback_data="admin_jobs_open")],
        [InlineKeyboardButton("🎉 Completed Jobs", callback_data="admin_jobs_completed")],
    ])
    await update.message.reply_text("📖 *Admin Job Panel*\n\nSelect a category to view jobs:", reply_markup=keyboard, parse_mode="Markdown")


async def admin_jobs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callbacks from the admin job menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != int(ADMIN_ID):
        await query.edit_message_text("⛔ Access denied.")
        return

    data = query.data
    if data == "admin_jobs_booked":
        await list_booked_jobs_for_admin(query)
    elif data == "admin_jobs_rejected":
        await list_rejected_jobs_for_admin(query)
    elif data == "admin_jobs_open":
        await list_open_jobs_for_admin(query)
    elif data == "admin_jobs_completed":
        await list_completed_jobs_for_admin(query)


async def list_booked_jobs_for_admin(query: CallbackQuery):
    jobs = await job_service.get_jobs_by_status("assigned")
    if not jobs:
        await query.edit_message_text("No booked jobs found.")
        return

    await query.edit_message_text("--- ✅ Booked Jobs ---")
    for job in jobs[:10]:  # Limit to 10 to prevent spam
        priest_id = job.get("assigned_priest")
        priest_info = "Unknown Priest"
        if priest_id:
            priest = await user_service.get_user_details(priest_id)
            priest_info = f"{priest.get('name', 'N/A')} (<code>{priest_id}</code>)" if priest else f"ID: <code>{priest_id}</code>"

        image_bytes = generate_job_image(job, theme="green")

        text = f"✅ <b>{job['title']}</b> at {job['location']}\n" \
               f"<b>Dakshina:</b> ₹{job.get('fees', 'N/A')} | <b>Date:</b> {job.get('date', 'N/A')} {job.get('time', '')}\n" \
               f"<b>Assigned to:</b> {priest_info}"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")


async def list_rejected_jobs_for_admin(query: CallbackQuery):
    jobs = await job_service.get_all_rejected_jobs()
    if not jobs:
        await query.edit_message_text("No jobs have been rejected yet.")
        return

    await query.edit_message_text("--- ❌ Rejected Jobs ---")
    for job in jobs[:10]:
        rejected_by_ids = job.get("rejected_by", [])
        rejected_by_info = "None"
        if rejected_by_ids:
            priests = await user_service.get_users_details(rejected_by_ids)
            priest_names = [f"{p.get('name', 'N/A')} (<code>{p['id']}</code>)" for p in priests]
            rejected_by_info = "\n - ".join(priest_names)

        image_bytes = generate_job_image(job, theme="red")

        text = f"❌ <b>{job['title']}</b> at {job['location']} (Status: {job.get('status')})\n" \
               f"<b>Rejected by:</b>\n - {rejected_by_info}"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")


async def list_open_jobs_for_admin(query: CallbackQuery):
    jobs = await job_service.get_jobs_by_status("open")
    if not jobs:
        await query.edit_message_text("No open jobs found.")
        return

    await query.edit_message_text("--- 📬 Open Jobs ---")
    for job in jobs[:10]:
        text = f"*{job['title']}* at {job['location']}\n" \
               f"Fees: ₹{job.get('fees', 'N/A')} | {job.get('date', 'N/A')}"
        await query.message.reply_text(text, parse_mode="Markdown")


async def list_completed_jobs_for_admin(query: CallbackQuery):
    jobs = await job_service.get_jobs_by_status("completed")
    if not jobs:
        await query.edit_message_text("No completed jobs found.")
        return

    await query.edit_message_text("--- 🎉 Completed Jobs ---")
    for job in jobs[:10]:
        priest_id = job.get("assigned_priest")
        priest_info = "Unknown Priest"
        if priest_id:
            priest = await user_service.get_user_details(priest_id)
            priest_info = f"{priest.get('name', 'N/A')} (<code>{priest_id}</code>)" if priest else f"ID: <code>{priest_id}</code>"

        image_bytes = generate_job_image(job, theme="green")

        text = f"🎉 <b>{job['title']}</b> at {job['location']}\n" \
               f"<b>Dakshina:</b> ₹{job.get('fees', 'N/A')} | <b>Date:</b> {job.get('date', 'N/A')} {job.get('time', '')}\n" \
               f"<b>Completed by:</b> {priest_info}"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")