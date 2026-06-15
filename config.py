import logging
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID")  # kept for backward compat (primary admin)
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_ID", "").split(",") if x.strip().isdigit()}
DATABASE_URL = os.getenv("DATABASE_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def is_admin(user_id: int) -> bool:
    """Returns True if the given Telegram user ID is an admin."""
    return user_id in ADMIN_IDS

if not BOT_TOKEN:
    raise EnvironmentError("BOT_TOKEN is required")

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL is required")

if not ADMIN_IDS:
    raise EnvironmentError("ADMIN_ID is required")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("aavhan")