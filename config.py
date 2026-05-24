import logging
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if not BOT_TOKEN:
    raise EnvironmentError("BOT_TOKEN is required")

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL is required")

if not ADMIN_ID:
    raise EnvironmentError("ADMIN_ID is required")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("aavhan")