import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes.webhook import router, set_telegram_app
from app.bot import create_bot
from app.db.postgres import init_db
from app.watchers.job_watcher import watch_jobs
from app.watchers.reminder_watcher import reminder_loop
from config import WEBHOOK_URL, BOT_TOKEN, logger

telegram_app = create_bot()
set_telegram_app(telegram_app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Telegram bot started")

    if WEBHOOK_URL:
        url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        info = await telegram_app.bot.get_webhook_info()
        if info.url != url:
            await telegram_app.bot.set_webhook(url)
    
    # Start the background watchers to listen for Neon DB changes
    asyncio.create_task(watch_jobs(telegram_app))
    asyncio.create_task(reminder_loop(telegram_app))
    yield

    await telegram_app.bot.delete_webhook()
    if telegram_app.running:
        await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

app.include_router(router)
