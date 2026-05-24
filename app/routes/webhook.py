from fastapi import APIRouter, Request
from telegram import Update

from config import BOT_TOKEN, logger

router = APIRouter()

telegram_app = None

def set_telegram_app(app):
    global telegram_app
    telegram_app = app

@router.post(f"/{BOT_TOKEN}")
async def webhook_handler(request: Request):
    """
    Receives updates from Telegram and pushes them into the bot's update queue.
    """
    if not telegram_app:
        logger.error("Webhook request received before bot initialization")
        return {"ok": False, "error": "Bot not initialized"}

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.exception("Error processing webhook update")
        return {"ok": False, "error": str(e)}