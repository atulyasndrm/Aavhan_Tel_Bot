import json
from app.db.postgres import db_pool
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.services.image_service import generate_job_image
from config import logger

async def broadcast_job(app, job):
    rejected_priests = [int(p) for p in (job.get("rejected_by", []) or [])]
    job_datetime = job.get("datetime")

    # Find all verified users who have NOT rejected this job and do NOT have a time conflict
    async with db_pool.acquire() as conn:
        query = "SELECT * FROM users u WHERE u.verified = TRUE"
        args = []

        if rejected_priests:
            # Inline IDs directly — safe because each is hard-cast to int above
            ids_literal = ",".join(str(p) for p in rejected_priests)
            query += f" AND NOT (u.id = ANY(ARRAY[{ids_literal}]::bigint[]))"

        if job_datetime:
            args.append(job_datetime)
            query += f""" AND NOT EXISTS (
                SELECT 1 FROM bookings b
                WHERE b.assigned_priest = u.id
                AND b.status = 'assigned'
                AND b.datetime < (${len(args)}::timestamp + interval '3 hours')
                AND ${len(args)}::timestamp < (b.datetime + interval '3 hours')
            )"""

        users = await conn.fetch(query, *args)

    # Generate the custom image dynamically from the job data
    image_bytes = generate_job_image(job)
    photo_to_send = image_bytes

    # Prepare beautiful broadcast text variables natively falling back on old formats
    title = job.get('title') or job.get('ceremony_type') or job.get('ceremonyType') or 'Vishesh Puja'
    host = job.get('host_name') or job.get('full_name') or job.get('fullName') or 'Bhakta'
    city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
    location = city_state if city_state else (job.get('location') or 'N/A')
    
    samagri_val = str(job.get('samagri') or '').lower()
    if 'pandit' in samagri_val:
        samagri = "Pandit Will Bring"
    elif 'yajman' in samagri_val or 'self' in samagri_val:
        samagri = "Yajman Will Arrange"
    else:
        samagri = str(job.get('samagri') or 'To be discussed')
        
    dakshina = f"₹ {job.get('fees')}" if job.get('fees') else "To be discussed"
    notes = f"\n\n<i>Note: {job.get('notes')}</i>" if job.get('notes') else ""

    messages_sent = []
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
            
            # Add message info to our list to be saved
            messages_sent.append({
                "chat_id": user["id"],
                "message_id": msg.message_id
            })

            # Cache the uploaded image file_id to send instantly to other priests
            if isinstance(photo_to_send, bytes):
                photo_to_send = msg.photo[-1].file_id
                
        except Exception as e:
            logger.exception("Error sending broadcast to %s", user.get('id'))

    # After loop, update the database with all message IDs
    if messages_sent:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE bookings SET broadcast_messages = $1 WHERE id = $2",
                json.dumps(messages_sent),
                job['id']
            )