# 🕉️ Aavhan - Priest Booking Telegram Bot

A production-ready Telegram bot that connects verified priests with religious job requests. Built with Python, PostgreSQL, FastAPI, and `python-telegram-bot`.

---

## ✨ Core Features

### For Priests
- KYC verification flow with Name, Phone, and Document upload.
- Receive open jobs as dynamic image cards.
- Apply, reject, or re-apply directly from Telegram.
- Interactive menu buttons to view job lists (`📿 Open Jobs`, `✅ Applied`, `❌ Rejected`, and `📜 History`).
- Edit profile to easily update contact details and ID documents (`✏️ Edit Profile`).
- Conflict detection to avoid scheduling overlapping work.
- Reminder notifications for upcoming assignments.

### For Admins
- Secure admin-only panel via `ADMIN_ID`.
- Interactive custom keyboards for seamless bot management.
- Approve or reject priest verification requests.
- Create and broadcast jobs using the interactive `➕ Create Job` flow.
- Send announcements to verified priests using `📢 Broadcast`.
- Search and manage priests by name, phone, or ID using `🔍 Find Priest`.
- Monitor open, booked, rejected, expired, and completed jobs.
- View visual **Analytics Dashboards** and **Top Priests Leaderboards**.
- Generate and download professional PDF reports for Jobs and Priests.

---

## 🛠️ Tech Stack

- Python 3.9+
- `python-telegram-bot` v20+
- FastAPI + Uvicorn
- PostgreSQL + `asyncpg`
- Pillow for image generation

---

## 📁 Project Structure

```text
app/
├── db/
│   └── postgres.py        # PostgreSQL pool and DB access
├── handlers/
│   ├── admin.py           # Admin verification and approvals
│   ├── auth.py            # Priest verification flow
│   ├── create_job.py      # Admin job creation flow
│   ├── help.py            # Help command handler
│   ├── job_actions.py     # Callback actions for jobs
│   ├── jobs.py            # `/jobs`, `/applied`, `/rejected`, `/history`
│   └── start.py           # Start command and greeting
├── services/
│   ├── admin_jobs.py      # Admin dashboard logic
│   ├── broadcast.py       # Job broadcast helpers
│   ├── conflict_service.py# Scheduling conflict checks
│   ├── image_service.py   # Job image card generator
│   ├── job_service.py     # Job queries and pagination
│   └── user_service.py    # User database queries
├── middleware/
│   └── auth.py            # Verification gatekeeping
├── routes/
│   └── webhook.py         # Webhook route for Telegram
├── watchers/
│   ├── job_watcher.py     # DB watcher for new jobs
│   └── reminder_watcher.py# Reminder scheduling watcher
└── bot.py                 # Application builder and handler registration
config.py                  # Environment config loader
main.py                    # FastAPI entrypoint
```

---

## ✅ Required Files

- `config.py`
- `requirements.txt`
- `main.py`
- `Dockerfile`
- `docker-compose.yml`
- `.env` or `.env.example`
- `app/bot.py`
- `app/routes/webhook.py`
- `app/db/postgres.py`
- `app/handlers/*.py`
- `app/services/*.py`
- `app/middleware/auth.py`
- `app/watchers/*.py`

---

## 🚀 Local Setup

### 1. Clone repository

```bash
git clone <your-repo-url>
cd Aavhan_Tel_Bot
```

### 2. Create virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env` and set your values:

```ini
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@localhost:5432/aavhan_db
ADMIN_ID=your_telegram_user_id
```

If you are using Neon PostgreSQL, use the Neon connection string and include `sslmode=require`:

```ini
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>?sslmode=require
```

### 5. Start PostgreSQL

Use Docker Compose or a local PostgreSQL instance.

```bash
docker-compose up -d
```

### 6. Run the app locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

> In development, you can add `--reload`, but avoid `--reload` in production.

---

## 🚢 Production Deployment

### Option 1: Docker Compose

```bash
docker-compose up -d --build
```

This starts the bot service and database together using the included `Dockerfile` and `docker-compose.yml`.

### Option 2: Direct Uvicorn (production)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production notes

- Use a dedicated PostgreSQL database and strong credentials.
- Keep `BOT_TOKEN` and `ADMIN_ID` secret.
- Use process supervision like `systemd`, `supervisor`, or Docker restart policies.
- Configure a webhook URL if you want Telegram webhooks instead of polling.

---

## 📌 Notes

- `app/services/image_service.py` generates job cards at runtime.
- `app/handlers/job_actions.py` handles callback buttons like apply, reject, and pagination (`more_jobs_`).
- `app/services/job_service.py` supports pagination with `limit` and `offset`.

---

## 📣 Support

For updates or troubleshooting, inspect logs and confirm that `ADMIN_ID` is correct and PostgreSQL is reachable.
