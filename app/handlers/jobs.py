import urllib.parse
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes


from app.services.job_service import get_available_jobs, get_applied_jobs, get_rejected_jobs, get_completed_jobs, get_priest_jobs_for_report
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

    jobs = await get_applied_jobs(user.id, limit=6, offset=0)

    if not jobs:
        await update.message.reply_text("📭 You haven't applied to any jobs yet.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    for job in jobs_to_show:
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

    if more_available:
        more_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Next Page ➡️", callback_data="more_applied_5")]
        ])
        await update.message.reply_text(
            "📌 More applied jobs are available. Show next batch?",
            reply_markup=more_keyboard
        )


async def list_rejected_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    jobs = await get_rejected_jobs(user.id, limit=6, offset=0)

    if not jobs:
        await update.message.reply_text("📭 You haven't rejected any jobs.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    for job in jobs_to_show:
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

    if more_available:
        more_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Next Page ➡️", callback_data="more_rejected_5")]
        ])
        await update.message.reply_text(
            "📌 More rejected jobs are available. Show next batch?",
            reply_markup=more_keyboard
        )


async def list_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    jobs = await get_completed_jobs(user.id, limit=6, offset=0)

    if not jobs:
        await update.message.reply_text("📭 You haven't completed any jobs yet.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    for job in jobs_to_show:
        image_bytes = generate_job_image(job, theme="completed")
        
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
        
    if more_available:
        more_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Next Page ➡️", callback_data="more_history_5")]
        ])
        await update.message.reply_text(
            "📌 More completed jobs are available. Show next batch?",
            reply_markup=more_keyboard
        )


async def download_priest_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user

    if not await is_verified(user.id):
        await update.message.reply_text("⛔ Complete verification first.")
        return

    status_msg = await update.message.reply_text("⏳ Generating your complete Puja report...")
    
    try:
        jobs = await get_priest_jobs_for_report(user.id)
        
        if not jobs:
            await status_msg.edit_text("📭 You haven't been assigned to any jobs yet.")
            return
            
        from app.services.pdf_service import generate_jobs_pdf
        pdf_bytes = generate_jobs_pdf(jobs)
        
        filename = f"My_Aavhan_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        caption = "📄 *Your Aavhan Jobs Report*\nHere is the complete list of all your assigned and completed Pujas."
        
        await update.message.reply_document(document=pdf_bytes, filename=filename, caption=caption, parse_mode="Markdown")
    except Exception as e:
        from config import logger
        logger.exception("Priest PDF generation failed")
        await update.message.reply_text(f"❌ Error generating report: {str(e)}")
    finally:
        await status_msg.delete()