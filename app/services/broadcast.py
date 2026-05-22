from app.db.postgres import db_pool
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.services.image_service import generate_job_image

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
🕉️ <b>{job['title']}</b>

<b>Location:</b> {job['location']}
<b>Date & Time:</b> {job.get('date', 'N/A')} {job.get('time', 'N/A')}
<b>Dakshina:</b> ₹{job.get('fees', 'N/A')}

🙏 <i>Please accept or reject this Aavhan.</i>
""",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            # Cache the uploaded image file_id to send instantly to other priests
            if isinstance(photo_to_send, bytes):
                photo_to_send = msg.photo[-1].file_id
                
        except Exception as e:
            print(f"Error sending broadcast to {user.get('id')}: {e}")