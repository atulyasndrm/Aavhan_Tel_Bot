from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes

from config import ADMIN_ID
from app.db.postgres import db_pool
from app.services import job_service, user_service
from app.services.image_service import generate_job_image


async def get_dashboard_summary():
    """Fetches real-time counts for the admin dashboard HUD."""
    async with db_pool.acquire() as conn:
        priests_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE verified = TRUE")
        pending_priests = await conn.fetchval("SELECT COUNT(*) FROM users WHERE verification_status = 'pending'")
        open_jobs = await conn.fetchval("SELECT COUNT(*) FROM bookings WHERE status IN ('open', 'new')")
        assigned_jobs = await conn.fetchval("SELECT COUNT(*) FROM bookings WHERE status = 'assigned'")
        completed_jobs = await conn.fetchval("SELECT COUNT(*) FROM bookings WHERE status = 'completed'")
        
    pending_text = f"  *(⏳ {pending_priests} pending)*" if pending_priests else ""
    
    return (
        " *Aavhan Master Dashboard*\n\n"
        " *Live Platform Stats:*\n"
        f" *Verified Priests:* `{priests_count}`{pending_text}\n"
        f" *Open Jobs:* `{open_jobs}`\n"
        f" *Assigned Jobs:* `{assigned_jobs}`\n"
        f" *Completed Jobs:* `{completed_jobs}`\n\n"
        " *Select an option below to manage operations:*"
    )


def get_admin_main_keyboard():
    """Returns the perfectly structured Admin Dashboard keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Analytics Dashboard", callback_data="admin_jobs_analytics")],
        [InlineKeyboardButton(" Open Jobs", callback_data="admin_jobs_open_0"),
         InlineKeyboardButton(" Booked Jobs", callback_data="admin_jobs_booked_0")],
        [InlineKeyboardButton(" Completed Jobs", callback_data="admin_jobs_completed_0"),
         InlineKeyboardButton(" Rejected Jobs", callback_data="admin_jobs_rejected_0")],
        [InlineKeyboardButton(" Expired Jobs", callback_data="admin_jobs_expired_0"),
         InlineKeyboardButton(" Top Priests", callback_data="admin_jobs_leaderboard")],
        [InlineKeyboardButton(" Jobs Report", callback_data="admin_jobs_pdf_jobs"),
         InlineKeyboardButton(" Priests Report", callback_data="admin_jobs_pdf_priests")],
    ])


async def admin_jobs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the admin job management menu."""
    if not update.message or update.effective_user.id != int(ADMIN_ID):
        return

    text = await get_dashboard_summary()
    keyboard = get_admin_main_keyboard()
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def admin_jobs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callbacks from the admin job menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != int(ADMIN_ID):
        await query.edit_message_text("⛔ Access denied.")
        return

    data = query.data
    if data == "admin_jobs_main":
        text = await get_dashboard_summary()
        keyboard = get_admin_main_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    parts = data.split("_")
    if len(parts) >= 3:
        category = parts[2]
        
        if category == "analytics":
            return await send_analytics_dashboard(query, context)

        if category == "leaderboard":
            return await handle_leaderboard(query)
            
        if category == "rebroadcast":
            job_id = parts[3]
            return await handle_rebroadcast(query, job_id)
            
        if category == "pdf":
            report_type = parts[3] if len(parts) > 3 else "jobs"
            return await send_pdf_report(query, context, report_type)
            
        offset = int(parts[3]) if len(parts) > 3 else 0
        
        if category == "booked":
            await list_booked_jobs_for_admin(query, offset)
        elif category == "rejected":
            await list_rejected_jobs_for_admin(query, offset)
        elif category == "open":
            await list_open_jobs_for_admin(query, offset)
        elif category == "completed":
            await list_completed_jobs_for_admin(query, offset)
        elif category == "expired":
            await list_expired_jobs_for_admin(query, offset)


async def list_booked_jobs_for_admin(query: CallbackQuery, offset: int):
    jobs = await job_service.get_jobs_by_status("assigned", limit=6, offset=offset)
    if not jobs:
        await query.edit_message_text("No booked jobs found.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    await query.edit_message_text(f"--- ✅ Booked Jobs (Page {offset//5 + 1}) ---")
    for job in jobs_to_show:
        priest_id = job.get("assigned_priest")
        priest_info = "Unknown Priest"
        if priest_id:
            priest = await user_service.get_user_details(priest_id)
            priest_info = f"{priest.get('name', 'N/A')} (<code>{priest_id}</code>)" if priest else f"ID: <code>{priest_id}</code>"

        image_bytes = generate_job_image(job, theme="green")

        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'Unknown Location')

        text = f"✅ <b>{title}</b> at {location}\n" \
               f"<b>Dakshina:</b> ₹{job.get('fees', 'N/A')} | <b>Date:</b> {job.get('date', 'N/A')} {job.get('time', '')}\n" \
               f"<b>Assigned to:</b> {priest_info}"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")
        
    await _send_pagination_nav(query, "booked", offset, more_available)


async def list_rejected_jobs_for_admin(query: CallbackQuery, offset: int):
    jobs = await job_service.get_all_rejected_jobs(limit=6, offset=offset)
    if not jobs:
        await query.edit_message_text("No jobs have been rejected yet.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    await query.edit_message_text(f"--- ❌ Rejected Jobs (Page {offset//5 + 1}) ---")
    for job in jobs_to_show:
        rejected_by_ids = job.get("rejected_by", [])
        rejected_by_info = "None"
        if rejected_by_ids:
            priests = await user_service.get_users_details(rejected_by_ids)
            priest_names = [f"{p.get('name', 'N/A')} (<code>{p['id']}</code>)" for p in priests]
            rejected_by_info = "\n - ".join(priest_names)

        image_bytes = generate_job_image(job, theme="red")

        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'Unknown Location')

        text = f"❌ <b>{title}</b> at {location} (Status: {job.get('status')})\n" \
               f"<b>Rejected by:</b>\n - {rejected_by_info}"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")
        
    await _send_pagination_nav(query, "rejected", offset, more_available)


async def list_open_jobs_for_admin(query: CallbackQuery, offset: int):
    jobs = await job_service.get_jobs_by_status("open", limit=6, offset=offset)
    if not jobs:
        await query.edit_message_text("No open jobs found.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    await query.edit_message_text(f"--- 📬 Open Jobs (Page {offset//5 + 1}) ---")
    for job in jobs_to_show:
        image_bytes = generate_job_image(job)

        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'Unknown Location')

        text = f"📬 <b>{title}</b> at {location}\n" \
               f"<b>Dakshina:</b> ₹{job.get('fees', 'N/A')} | <b>Date:</b> {job.get('date', 'N/A')} {job.get('time', '')}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Re-Broadcast", callback_data=f"admin_jobs_rebroadcast_{job['id']}")]
        ])
        await query.message.reply_photo(photo=image_bytes, caption=text, reply_markup=keyboard, parse_mode="HTML")
        
    await _send_pagination_nav(query, "open", offset, more_available)


async def list_completed_jobs_for_admin(query: CallbackQuery, offset: int):
    jobs = await job_service.get_jobs_by_status("completed", limit=6, offset=offset)
    if not jobs:
        await query.edit_message_text("No completed jobs found.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    await query.edit_message_text(f"--- 🎉 Completed Jobs (Page {offset//5 + 1}) ---")
    for job in jobs_to_show:
        priest_id = job.get("assigned_priest")
        priest_info = "Unknown Priest"
        if priest_id:
            priest = await user_service.get_user_details(priest_id)
            priest_info = f"{priest.get('name', 'N/A')} (<code>{priest_id}</code>)" if priest else f"ID: <code>{priest_id}</code>"

        image_bytes = generate_job_image(job, theme="completed")

        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'Unknown Location')

        text = f"🎉 <b>{title}</b> at {location}\n" \
               f"<b>Dakshina:</b> ₹{job.get('fees', 'N/A')} | <b>Date:</b> {job.get('date', 'N/A')} {job.get('time', '')}\n" \
               f"<b>Completed by:</b> {priest_info}"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")
        
    await _send_pagination_nav(query, "completed", offset, more_available)


async def list_expired_jobs_for_admin(query: CallbackQuery, offset: int):
    jobs = await job_service.get_expired_unassigned_jobs(limit=6, offset=offset)
    if not jobs:
        await query.edit_message_text("No expired unassigned jobs found.")
        return

    jobs_to_show = jobs[:5]
    more_available = len(jobs) > 5

    await query.edit_message_text(f"--- ⏰ Expired Jobs (Page {offset//5 + 1}) ---")
    for job in jobs_to_show:
        image_bytes = generate_job_image(job, theme="red")

        title = job.get('title') or job.get('ceremony_type') or 'Vishesh Puja'
        city_state = f"{job.get('city') or ''}, {job.get('state') or ''}".strip(', ').strip()
        location = city_state if city_state else (job.get('location') or 'Unknown Location')

        text = f"⏰ <b>{title}</b> at {location}\n" \
               f"<b>Dakshina:</b> ₹{job.get('fees', 'N/A')} | <b>Date:</b> {job.get('date', 'N/A')} {job.get('time', '')}\n" \
               f"<b>Status:</b> Expired / Unassigned"
        await query.message.reply_photo(photo=image_bytes, caption=text, parse_mode="HTML")
        
    await _send_pagination_nav(query, "expired", offset, more_available)


async def _send_pagination_nav(query: CallbackQuery, category: str, offset: int, more_available: bool):
    nav_keyboard = []
    if more_available:
        nav_keyboard.append([InlineKeyboardButton("Next Page ➡️", callback_data=f"admin_jobs_{category}_{offset+5}")])
    nav_keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_jobs_main")])
    
    await query.message.reply_text(
        "📌 Navigation:",
        reply_markup=InlineKeyboardMarkup(nav_keyboard)
    )


async def handle_rebroadcast(query: CallbackQuery, job_id: str):
    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE bookings 
            SET broadcast_status = 'pending', 
                next_broadcast_at = CURRENT_TIMESTAMP, 
                broadcast_attempts = 0 
            WHERE id = $1::uuid AND status IN ('open', 'new')
        """, job_id)
        
    if result.endswith("0"):
        await query.answer("❌ Job not found or is already assigned.", show_alert=True)
    else:
        await query.answer("✅ Job queued for background re-broadcast!", show_alert=True)


async def send_pdf_report(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, report_type: str):
    await query.answer("Generating PDF... Please wait.")
    
    status_msg = await query.message.reply_text(f"⏳ Generating complete {report_type.capitalize()} Report...")
    try:
        if report_type == "priests":
            users = await user_service.get_all_users_for_report()
            
            if not users:
                await status_msg.edit_text("❌ No priests found to generate a report.")
                return
                
            from app.services.pdf_service import generate_priests_pdf
            pdf_bytes = generate_priests_pdf(users)
            
            filename = f"Aavhan_Priests_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            caption = "📄 *Aavhan Priests Report*\nHere is the complete list of all priests grouped by verification status."
        else:
            jobs = await job_service.get_all_jobs_for_report()
            
            if not jobs:
                await status_msg.edit_text("❌ No jobs found to generate a report.")
                return
                
            from app.services.pdf_service import generate_jobs_pdf
            pdf_bytes = generate_jobs_pdf(jobs)
            
            filename = f"Aavhan_Jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            caption = "📄 *Aavhan Master Report*\nHere is the complete list of all jobs grouped by their status."

        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=pdf_bytes,
            filename=filename,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        from config import logger
        logger.exception("PDF generation failed")
        await query.message.reply_text(f"❌ Error generating report: {str(e)}")
    finally:
        await status_msg.delete()


async def send_analytics_dashboard(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    await query.answer("Drawing charts... Please wait.")
    status_msg = await query.message.reply_text("📊 Generating Analytics Dashboard...")
    
    try:
        from app.services.analytics_service import generate_analytics_image
        image_bytes = await generate_analytics_image()
        
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=image_bytes,
            caption="📊 *Aavhan Analytics Dashboard*\n\nHere is a real-time visual breakdown of your platform's performance.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Error generating dashboard: {str(e)}")
    finally:
        await status_msg.delete()


async def handle_leaderboard(query: CallbackQuery):
    priests = await user_service.get_top_priests(10)
    
    if not priests:
        await query.answer("No completed jobs yet to rank priests!", show_alert=True)
        return
        
    text = "🏆 *Aavhan Top Priests Leaderboard*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for idx, p in enumerate(priests):
        rank = medals[idx] if idx < 3 else f"*{idx+1}.*"
        name = p.get('name', 'Unknown')
        jobs = p.get('completed_jobs', 0)
        phone = p.get('phone', 'N/A')
        
        text += f"{rank} {name} ({jobs} Pujas completed)\n"
        text += f"      📞 {phone} | 🆔 `{p['id']}`\n\n"
        
    text += "🌟 _These are your most active and reliable Pandits!_"
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="admin_jobs_main")]])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")