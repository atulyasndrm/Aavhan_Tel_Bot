import io
from datetime import timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from app.services.conflict_service import has_conflict
from app.services.broadcast import broadcast_job
from app.services.image_service import generate_job_image
from app.services.job_service import get_available_jobs
from config import ADMIN_ID, logger

from app.db.postgres import db_pool


async def job_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    async def edit_reply(new_text):
        # Automatically detect if the message is an image (broadcast) or text (/jobs command)
        if query.message and getattr(query.message, "photo", None):
            await query.edit_message_caption(caption=new_text)
        else:
            await query.edit_message_text(text=new_text)

    # ===== APPLY =====
    if data.startswith("apply_job_"):
        job_id = data.split("_")[2]

        async with db_pool.acquire() as conn:
            job = await conn.fetchrow("SELECT * FROM bookings WHERE id = $1::uuid", job_id)

        if not job:
           await edit_reply("❌ Job not found.")
           return

        if job.get("status") not in ["open", "new"]:
           await edit_reply("❌ Job already taken.")
           return
       
        job_datetime = job.get("datetime")
        if job_datetime and await has_conflict(user_id, job_datetime):
           await edit_reply("⛔ Time conflict! You already have a nearby booking.")
           return

        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE bookings SET status = 'assigned', assigned_priest = $1 
                WHERE id = $2::uuid
            """, user_id, job_id)

        await edit_reply("✅ You applied successfully!")

        # Notify Admin
        try:
            priest_name = query.from_user.full_name
            job_title = job.get('title') or job.get('ceremony_type') or 'Unknown Puja'
            admin_text = (
                f"✅ *Job Accepted*\n\n"
                f"👤 *Priest:* {priest_name} (`{user_id}`)\n"
                f"📿 *Job:* {job_title}\n\n"
                f"ℹ️ _The job is now assigned to this priest._"
            )
            await context.bot.send_message(
                chat_id=int(ADMIN_ID), 
                text=admin_text, 
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception("Error notifying admin about acceptance")

    # ===== REJECT =====
    elif data.startswith("reject_job_"):
       job_id = data.split("_")[2]

       async with db_pool.acquire() as conn:
           await conn.execute("""
               UPDATE bookings SET rejected_by = array_append(rejected_by, $1) 
               WHERE id = $2::uuid AND NOT ($1 = ANY(COALESCE(rejected_by, '{}'::BIGINT[])))
           """, user_id, job_id)

       await edit_reply("❌ Job hidden for you.")

    # ===== CANCEL / WITHDRAW =====
    elif data.startswith("cancel_job_"):
       job_id = data.split("_")[2]

       async with db_pool.acquire() as conn:
           result = await conn.execute("""
               UPDATE bookings 
               SET status = 'open', 
                   assigned_priest = NULL, 
                   rejected_by = array_append(COALESCE(rejected_by, '{}'::BIGINT[]), $1) 
               WHERE id = $2::uuid AND assigned_priest = $1
           """, user_id, job_id)
           
           # UPDATE returns "UPDATE <count>" e.g., "UPDATE 1"
           modified_count = int(result.split()[-1])

       if modified_count > 0:
           # Fetch the updated job to broadcast
           async with db_pool.acquire() as conn:
               job_to_broadcast = await conn.fetchrow("SELECT * FROM bookings WHERE id = $1::uuid", job_id)
               
           if job_to_broadcast:
               await broadcast_job(context.application, job_to_broadcast)
           
               # Notify the Admin
               try:
                   priest_name = query.from_user.full_name
                   job_title = job_to_broadcast.get('title', 'Unknown Puja')
                   admin_text = (
                       f"⚠️ *Job Assignment Cancelled*\n\n"
                       f"👤 *Priest:* {priest_name} (`{user_id}`)\n"
                       f"📿 *Job:* {job_title}\n\n"
                       f"ℹ️ _The job has been automatically re-listed._"
                   )
                   await context.bot.send_message(
                       chat_id=int(ADMIN_ID), 
                       text=admin_text, 
                       parse_mode="Markdown"
                   )
               except Exception as e:
                   logger.exception("Error notifying admin about cancel")
           await edit_reply("❌ You have cancelled your assignment. The job has been re-listed for other priests.")
       else:
           await edit_reply("Could not cancel. The job may no longer be assigned to you.")

    # ===== SHOW MORE JOBS =====
    elif data.startswith("more_jobs_"):
        offset = int(data.split("_")[2])
        jobs = await get_available_jobs(query.from_user.id, limit=6, offset=offset)

        if not jobs:
            await edit_reply("📭 No more jobs available.")
            return

        jobs_to_show = jobs[:5]
        more_available = len(jobs) > 5

        for job in jobs_to_show:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Apply", callback_data=f"apply_job_{job['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_job_{job['id']}")
                ]
            ])

            image_bytes = generate_job_image(job)
            city = job.get('city') or ''
            state = job.get('state') or ''
            city_state = f"{city}, {state}".strip(', ').strip()
            location = city_state if city_state else (job.get('location') or 'N/A')
            title = job.get('title') or job.get('ceremony_type') or job.get('ceremonyType') or 'Vishesh Puja'
            text = (
                f"📿 <b>{title}</b>\n"
                f"<b>Location:</b> {location}\n"
                f"<b>Date & Time:</b> {job.get('date') or 'N/A'} {job.get('time') or 'N/A'}\n"
                f"<b>Dakshina:</b> ₹{job.get('fees') or 'N/A'}"
            )

            await query.message.reply_photo(
                photo=image_bytes,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        if more_available:
            next_offset = offset + 5
            more_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("More jobs", callback_data=f"more_jobs_{next_offset}")]
            ])
            await query.message.reply_text(
                "📌 More open jobs are available. Show next batch?",
                reply_markup=more_keyboard
            )
            await edit_reply("✅ Shown next jobs. Tap below to continue.")
        else:
            await edit_reply("✅ No more jobs available.")

    # ===== RE-APPLY =====
    elif data.startswith("reapply_job_"):
        job_id = data.split("_")[2]

        async with db_pool.acquire() as conn:
            job = await conn.fetchrow("SELECT * FROM bookings WHERE id = $1::uuid", job_id)

        if not job:
           await edit_reply("❌ Job not found.")
           return

        if job.get("status") not in ["open", "new"]:
           await edit_reply("❌ Job already taken by another priest.")
           return
       
        job_datetime = job.get("datetime")
        if job_datetime and await has_conflict(user_id, job_datetime):
           await edit_reply("⛔ Time conflict! You already have a nearby booking.")
           return

        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE bookings SET status = 'assigned', assigned_priest = $1, 
                rejected_by = array_remove(rejected_by, $1) 
                WHERE id = $2::uuid
            """, user_id, job_id)

        await edit_reply("✅ You successfully re-applied and got the job!")

        # Notify Admin
        try:
            priest_name = query.from_user.full_name
            job_title = job.get('title') or job.get('ceremony_type') or 'Unknown Puja'
            admin_text = (
                f"🔄 *Job Re-Accepted*\n\n"
                f"👤 *Priest:* {priest_name} (`{user_id}`)\n"
                f"📿 *Job:* {job_title}\n\n"
                f"ℹ️ _The job is now assigned to this priest after a re-application._"
            )
            await context.bot.send_message(
                chat_id=int(ADMIN_ID), 
                text=admin_text, 
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception("Error notifying admin about re-acceptance")

    # ===== COMPLETE =====
    elif data.startswith("complete_job_"):
        job_id = data.split("_")[2]

        async with db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE bookings SET status = 'completed' 
                WHERE id = $1::uuid AND assigned_priest = $2
            """, job_id, user_id)
            modified_count = int(result.split()[-1])

        if modified_count > 0:
            await edit_reply("✅ You have successfully marked this Puja as completed!")
            
            # Notify Admin
            try:
                async with db_pool.acquire() as conn:
                    job = await conn.fetchrow("SELECT * FROM bookings WHERE id = $1::uuid", job_id)
                    
                priest_name = query.from_user.full_name
                job_title = job.get('title', 'Unknown Puja') if job else 'Unknown Puja'
                admin_text = (
                    f"✅ *Puja Completed*\n\n"
                    f"👤 *Priest:* {priest_name} (`{user_id}`)\n"
                    f"📿 *Job:* {job_title}\n\n"
                    f"ℹ️ _The priest has marked this job as completed._"
                )
                await context.bot.send_message(
                    chat_id=int(ADMIN_ID), 
                    text=admin_text, 
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.exception("Error notifying admin about completion")
        else:
            await edit_reply("❌ Could not complete the job. It may already be completed or reassigned.")

    # ===== ADD TO CALENDAR =====
    elif data.startswith("calendar_job_"):
        job_id = data.split("_")[2]

        async with db_pool.acquire() as conn:
            job = await conn.fetchrow("SELECT * FROM bookings WHERE id = $1::uuid", job_id)

        if not job:
            return

        dtstart = job.get('datetime')
        if not dtstart:
            return

        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        location = job.get('location') or 'Yajman House'
        # Assume a standard 3-hour duration for the calendar event
        dtend = dtstart + timedelta(hours=3)
        fmt = "%Y%m%dT%H%M%S"

        ics_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Aavhan//Bot//EN\nBEGIN:VEVENT\nSUMMARY:{title}\nDTSTART:{dtstart.strftime(fmt)}\nDTEND:{dtend.strftime(fmt)}\nLOCATION:{location}\nDESCRIPTION:Dakshina: {job.get('fees', 'TBD')}\\nSamagri: {job.get('samagri', 'TBD')}\nEND:VEVENT\nEND:VCALENDAR"
        
        ics_file = io.BytesIO(ics_content.encode('utf-8'))
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"{safe_title.replace(' ', '_')}.ics"

        await context.bot.send_document(
            chat_id=user_id,
            document=ics_file,
            filename=filename,
            caption="📅 Open this file to instantly add the Puja to your phone's calendar!"
        )