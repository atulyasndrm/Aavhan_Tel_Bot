import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN=os.getenv("BOT_TOKEN")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

MONGO_URI = os.getenv("MONGO_URI")

ADMIN_ID = os.getenv("ADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL")