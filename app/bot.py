from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)

from config import BOT_TOKEN

# handlers
from app.handlers.start import start
from app.handlers.admin import admin_callback, admin_broadcast
from app.services.admin_jobs import admin_jobs_menu, admin_jobs_callback
from app.handlers.jobs import list_jobs, list_applied_jobs, list_rejected_jobs, list_history
from app.handlers.job_actions import job_callback
from app.handlers.help import help_command

from app.handlers.auth import (
    start_verification,
    get_name,
    get_phone,
    get_document,
    NAME,
    PHONE,
    DOCUMENT
)
from app.handlers.create_job import create_job_conv


def create_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ===== Conversation =====
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("verify", start_verification),
            CommandHandler("start", start)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            DOCUMENT: [MessageHandler(filters.ALL, get_document)],
        },
        fallbacks=[],
    )

    app.add_handler(create_job_conv)

    # ===== Commands =====
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("jobs", list_jobs))
    app.add_handler(CommandHandler("applied", list_applied_jobs))
    app.add_handler(CommandHandler("rejected", list_rejected_jobs))
    app.add_handler(CommandHandler("history", list_history))
    app.add_handler(CommandHandler("admin_jobs", admin_jobs_menu))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(conv_handler)

    # ===== Callback handlers (FIXED) =====
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^(approve_user_|reject_user_)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_jobs_callback,
            pattern="^admin_jobs_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            job_callback,
            pattern="^(apply_job_|reject_job_|cancel_job_|reapply_job_|complete_job_|more_jobs_)"
        )
    )

    return app