import asyncio
import logging
from datetime import datetime
from app.db.postgres import db_pool
from config import logger


async def reminder_loop(app):
    logger.info("Reminder system started")

    while True:
        try:
            # Use local time to match the time saved by your /create_job handler
            now = datetime.now() 

            async with db_pool.acquire() as conn:
                jobs = await conn.fetch("SELECT * FROM bookings WHERE status = 'assigned'")
                
            for job in jobs:
                job_time = job.get("datetime")

                # ✅ safety (avoid crash if datetime is NULL)
                if not job_time:
                    continue

                priest_id = job.get("assigned_priest")

                if not priest_id:
                    continue

                diff = (job_time - now).total_seconds()

                # skip past jobs
                if diff <= 0:
                    continue
                    
                sent = job.get("reminders_sent") or []

                # Trigger only the most urgent reminder & cascade skip the older ones
                if diff <= 3600:
                    if "1h" not in sent:
                        await send_reminder(app, priest_id, job, "1h")
                elif diff <= 7200:
                    if "2h" not in sent:
                        await send_reminder(app, priest_id, job, "2h")
                elif diff <= 86400:
                    if "24h" not in sent:
                        await send_reminder(app, priest_id, job, "24h")
        except Exception as e:
            logger.error("Error in reminder loop: %s", e)

        await asyncio.sleep(60)

def format_time_left(seconds):
    if seconds <= 0:
        return "Starting now"

    minutes = int(seconds // 60)
    hours = int(minutes // 60)

    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    elif minutes > 0:
        return f"{minutes} minutes"
    else:
        return f"{int(seconds)} sec"


def format_datetime(dt):
    return dt.strftime("%d %b, %I:%M %p")


async def send_reminder(app, user_id, job, tag):
    try:
        now = datetime.now()
        job_time = job.get("datetime")

        diff = (job_time - now).total_seconds()
        time_left = format_time_left(diff)

        # 🎯 tag styling
        if tag == "24h":
            title = "🔔 Reminder — Tomorrow"
            emoji = "🕊️"
        elif tag == "2h":
            title = "⚠️ Reminder — 2 Hours Left"
            emoji = "⏳"
        elif tag == "1h":
            title = "🚨 URGENT — 1 Hour Left"
            emoji = "🔥"
        else:
            title = "🔔 Reminder"
            emoji = "📿"

        text = f"""
{title}

{emoji} *{job['title']}*
Location: {job['location']}

Scheduled: {format_datetime(job_time)}
Time left: {time_left}

🙏 Please be ready before time.
"""

        await app.bot.send_message(
            chat_id=user_id,
            text=text.strip(),
            parse_mode="Markdown"
        )

        # ✅ mark sent and cascade skip older tags to prevent staggered spam on urgent jobs
        tags_to_add = [tag]
        if tag == "1h":
            tags_to_add = ["1h", "2h", "24h"]
        elif tag == "2h":
            tags_to_add = ["2h", "24h"]
            
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE bookings 
                SET reminders_sent = array_cat(reminders_sent, $1::text[]) 
                WHERE id = $2
            """, tags_to_add, job["id"])

    except Exception as e:
        logger.exception("Reminder error")