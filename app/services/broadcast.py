from app.db.postgres import db_pool
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.services.image_service import generate_job_image
from config import logger

async def broadcast_job(app, job):
    rejected_priests = job.get("rejected_by", []) or []

    # Find all verified users who have NOT rejected this job
    async with db_pool.acquire() as conn:
        if rejected_priests:
            users = await conn.fetch("SELECT * FROM users WHERE verified = TRUE AND NOT (id = ANY($1::bigint[]))", rejected_priests)
        else:
            users = await conn.fetch("SELECT * FROM users WHERE verified = TRUE")

    # Generate the custom image dynamically from the job data
    image_bytes = generate_job_image(job)
    photo_to_send = image_bytes

    # Prepare beautiful broadcast text variables natively falling back on old formats
    title = job.get('title') or job.get('ceremony_type') or job.get('ceremonyType') or 'Vishesh Puja'
    host = job.get('host_name') or job.get('full_name') or job.get('fullName') or 'Bhakta'
    city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
    location = city_state if city_state else (job.get('location') or 'N/A')
    
    samagri_val = str(job.get('samagri') or '').lower()
    samagri = "Pandit Will Bring" if 'pandit' in samagri_val else "Yajman Will Arrange" if 'self' in samagri_val else "To be discussed"
    dakshina = f"₹ {job.get('fees')}" if job.get('fees') else "To be discussed"
    notes = f"\n\n<i>Note: {job.get('notes')}</i>" if job.get('notes') else ""

    for user in users:
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

        try:
            msg = await app.bot.send_photo(
                chat_id=user["id"],
                photo=photo_to_send,
                caption=f"""
🕉️ <b>{title}</b>

<b>Host:</b> {host}
<b>Location:</b> {location}
<b>Date & Time:</b> {job.get('date', 'N/A')} {job.get('time', 'N/A')}
<b>Samagri:</b> {samagri}
<b>Dakshina:</b> {dakshina}{notes}

🙏 <i>Please accept or reject this Aavhan.</i>
""",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            # Cache the uploaded image file_id to send instantly to other priests
            if isinstance(photo_to_send, bytes):
                photo_to_send = msg.photo[-1].file_id
                
        except Exception as e:
            logger.exception("Error sending broadcast to %s", user.get('id'))