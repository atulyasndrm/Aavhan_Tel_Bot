import urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes


from app.services.job_service import get_available_jobs, get_applied_jobs, get_rejected_jobs, get_completed_jobs
from app.middleware.auth import is_verified
from app.services.image_service import generate_job_image


async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    jobs = await get_available_jobs(user.id, limit=6, offset=0)

    if not jobs:
        await update.message.reply_text("📭 No jobs available.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    for job in jobs_to_show:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Apply",
                    callback_data=f"apply_job_{job['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Reject",
                    callback_data=f"reject_job_{job['id']}"
                )
            ]
        ])

        image_bytes = generate_job_image(job)

        city = job.get('city') or ''
        state = job.get('state') or ''
        city_state = f"{city}, {state}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'N/A')
        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'

        text = (
            f"📿 <b>{title}</b>\n"
            f"<b>Location:</b> {location}\n"
            f"<b>Date & Time:</b> {job.get('date') or 'N/A'} {job.get('time') or 'N/A'}\n"
            f"<b>Dakshina:</b> ₹{job.get('fees') or 'N/A'}"
        )

        await update.message.reply_photo(
            photo=image_bytes,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    if more_available:
        more_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("More jobs", callback_data="more_jobs_5")]
        ])
        await update.message.reply_text(
            "📌 More open jobs are available. Show next batch?",
            reply_markup=more_keyboard
        )

async def list_applied_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    jobs = await get_applied_jobs(user.id)

    if not jobs:
        await update.message.reply_text("📭 You haven't applied to any jobs yet.")
        return

    jobs = jobs[:5]

    for job in jobs:
        city = job.get('city') or ''
        state = job.get('state') or ''
        city_state = f"{city}, {state}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'N/A')
        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        
        encoded_loc = urllib.parse.quote(location)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_loc}"

        buttons = []
        if job.get('status', 'assigned') == 'assigned':
            buttons = [
                [
                    InlineKeyboardButton("🚗 Navigate", url=maps_url),
                    InlineKeyboardButton("📅 Add to Calendar", callback_data=f"calendar_job_{job['id']}")
                ],
                [
                    InlineKeyboardButton("✅ Mark Completed", callback_data=f"complete_job_{job['id']}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_job_{job['id']}")
                ]
            ]
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        image_bytes = generate_job_image(job, theme="green")

        text = (
            f"✅ <b>{title}</b>\n"
            f"<b>Location:</b> {location}\n"
            f"<b>Date & Time:</b> {job.get('date') or 'N/A'} {job.get('time') or 'N/A'}\n"
            f"<b>Dakshina:</b> ₹{job.get('fees') or 'N/A'}\n"
            f"<b>Status:</b> {job.get('status', 'assigned').capitalize()}"
        )
        await update.message.reply_photo(photo=image_bytes, caption=text, reply_markup=keyboard, parse_mode="HTML")


async def list_rejected_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    jobs = await get_rejected_jobs(user.id)

    if not jobs:
        await update.message.reply_text("📭 You haven't rejected any jobs.")
        return

    jobs = jobs[:5]

    for job in jobs:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 Re-apply",
                    callback_data=f"reapply_job_{job['id']}"
                )
            ]
        ])

        image_bytes = generate_job_image(job, theme="red")
        
        city = job.get('city') or ''
        state = job.get('state') or ''
        city_state = f"{city}, {state}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'N/A')
        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'

        text = (
            f"❌ <b>{title}</b>\n"
            f"<b>Location:</b> {location}\n"
            f"<b>Date & Time:</b> {job.get('date') or 'N/A'} {job.get('time') or 'N/A'}\n"
            f"<b>Dakshina:</b> ₹{job.get('fees') or 'N/A'}"
        )
        await update.message.reply_photo(photo=image_bytes, caption=text, reply_markup=keyboard, parse_mode="HTML")


async def list_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    jobs = await get_completed_jobs(user.id)

    if not jobs:
        await update.message.reply_text("📭 You haven't completed any jobs yet.")
        return

    for job in jobs[:5]:
        image_bytes = generate_job_image(job, theme="green")
        
        city = job.get('city') or ''
        state = job.get('state') or ''
        city_state = f"{city}, {state}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'N/A')
        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        
        text = (
            f"🎉 <b>{title}</b>\n"
            f"<b>Location:</b> {location}\n"
            f"<b>Date & Time:</b> {job.get('date') or 'N/A'} {job.get('time') or 'N/A'}\n"
            f"<b>Dakshina:</b> ₹{job.get('fees') or 'N/A'}"
        )
        await update.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")