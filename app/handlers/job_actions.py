from telegram import Update
from telegram.ext import ContextTypes
from app.services.conflict_service import has_conflict
from app.services.broadcast import broadcast_job
from config import ADMIN_ID

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
            job = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)

        if not job:
           await edit_reply("❌ Job not found.")
           return

        if job.get("status") != "open":
           await edit_reply("❌ Job already taken.")
           return
       
        job_datetime = job.get("datetime")
        if job_datetime and await has_conflict(user_id, job_datetime):
           await edit_reply("⛔ Time conflict! You already have a nearby booking.")
           return

        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE jobs SET status = 'assigned', assigned_priest = $1 
                WHERE id = $2
            """, user_id, job_id)

        await edit_reply("✅ You applied successfully!")

    # ===== REJECT =====
    elif data.startswith("reject_job_"):
       job_id = data.split("_")[2]

       async with db_pool.acquire() as conn:
           await conn.execute("""
               UPDATE jobs SET rejected_by = array_append(rejected_by, $1) 
               WHERE id = $2 AND NOT ($1 = ANY(rejected_by))
           """, user_id, job_id)

       await edit_reply("❌ Job hidden for you.")

    # ===== CANCEL / WITHDRAW =====
    elif data.startswith("cancel_job_"):
       job_id = data.split("_")[2]

       async with db_pool.acquire() as conn:
           result = await conn.execute("""
               UPDATE jobs 
               SET status = 'open', 
                   assigned_priest = NULL, 
                   rejected_by = array_append(rejected_by, $1) 
               WHERE id = $2 AND assigned_priest = $1
           """, user_id, job_id)
           
           # UPDATE returns "UPDATE <count>" e.g., "UPDATE 1"
           modified_count = int(result.split()[-1])

       if modified_count > 0:
           # Fetch the updated job to broadcast
           async with db_pool.acquire() as conn:
               job_to_broadcast = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
               
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
                   print(f"Error notifying admin: {e}")
           
           await edit_reply("❌ You have cancelled your assignment. The job has been re-listed for other priests.")
       else:
           await edit_reply("Could not cancel. The job may no longer be assigned to you.")

    # ===== RE-APPLY =====
    elif data.startswith("reapply_job_"):
        job_id = data.split("_")[2]

        async with db_pool.acquire() as conn:
            job = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)

        if not job:
           await edit_reply("❌ Job not found.")
           return

        if job.get("status") != "open":
           await edit_reply("❌ Job already taken by another priest.")
           return
       
        job_datetime = job.get("datetime")
        if job_datetime and await has_conflict(user_id, job_datetime):
           await edit_reply("⛔ Time conflict! You already have a nearby booking.")
           return

        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE jobs SET status = 'assigned', assigned_priest = $1, 
                rejected_by = array_remove(rejected_by, $1) 
                WHERE id = $2
            """, user_id, job_id)

        await edit_reply("✅ You successfully re-applied and got the job!")

    # ===== COMPLETE =====
    elif data.startswith("complete_job_"):
        job_id = data.split("_")[2]

        async with db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE jobs SET status = 'completed' 
                WHERE id = $1 AND assigned_priest = $2
            """, job_id, user_id)
            modified_count = int(result.split()[-1])

        if modified_count > 0:
            await edit_reply("✅ You have successfully marked this Puja as completed!")
            
            # Notify Admin
            try:
                async with db_pool.acquire() as conn:
                    job = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
                    
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
                print(f"Error notifying admin about completion: {e}")
        else:
            await edit_reply("❌ Could not complete the job. It may already be completed or reassigned.")