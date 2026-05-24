# 🕉️ Aavhan: Event-Driven Priest Booking Platform

[!Python 3.9+](https://www.python.org/downloads/)
[!FastAPI](https://fastapi.tiangolo.com)
[!PostgreSQL](https://www.postgresql.org/)

**Aavhan** is a highly concurrent, asynchronous Telegram bot serving as a two-sided marketplace connecting verified Hindu Priests (Pandits) with devotees (Yajmans). Built for scale, it leverages an event-driven architecture using PostgreSQL `LISTEN/NOTIFY` pub/sub mechanisms, FastAPI, and `python-telegram-bot` to handle real-time job dispatching.

---

## ✨ Platform Capabilities

### 📿 Priest Interface (Client)
- **Frictionless Onboarding**: Automated KYC flow with state-machine-driven data collection and ID verification.
- **Real-Time Dispatch**: Instantaneous job broadcasts via dynamically generated, cached `PIL` image cards.
- **Atomic Transactions**: Race-condition-free job claiming using row-level database locks (eliminating double-bookings).
- **Smart Logistics**: One-tap deep-linking for Google Maps navigation and dynamic `.ics` calendar payload generation.
- **Client Dashboards**: Paginated interfaces for open, applied, and completed jobs, plus on-the-fly PDF portfolio generation.

###  Admin Control Plane (Backoffice)
- **Role-Based Access Control (RBAC)**: Secure, `ADMIN_ID`-gated command execution and middleware.
- **Live HUD Dashboard**: Real-time aggregate statistics (Verification Queues, Job States, GMV).
- **Data Export & Analytics**: Headless, thread-safe visualization generation (`matplotlib`) and tabular PDF reports (`reportlab`).
- **Entity Management**: Inline approval/rejection workflows, dynamic search filtering, and granular broadcast controls.

---

## 🏗️ System Architecture

- **API Layer**: `FastAPI` providing an ASGI interface for potential webhook integration and health checks.
- **Bot Engine**: `python-telegram-bot` (v20+) running in `async` mode.
- **Persistence**: `PostgreSQL` accessed via `asyncpg` connection pooling for maximum I/O throughput.
- **Event Loop**: Background `asyncio` watchers listening to PG triggers (`pg_notify`) to immediately dispatch jobs without polling overhead.
- **Design Pattern**: Service-Repository pattern (Handlers manage Telegram Context -> Services contain business logic -> DB handles persistence).

---

## 📂 Codebase Topography

```bash
app/
├── db/
│   └── postgres.py        # Connection pooling and schema migrations
├── handlers/
│   ├── admin.py           # Verification gating & search interfaces
│   ├── auth.py            # ConversationHandlers for KYC flow
│   ├── job_actions.py     # Inline keyboard callback routing
│   └── ...                # Additional state handlers
├── services/
│   ├── analytics_service.py # Headless Matplotlib generation
│   ├── pdf_service.py       # ReportLab PDF pipeline
│   ├── conflict_service.py  # Temporal overlap detection
│   └── image_service.py     # Pillow (PIL) graphic generation
├── middleware/
│   └── auth.py            # Route decorators for verified status
├── watchers/
│   ├── job_watcher.py     # asyncpg LISTEN/NOTIFY daemon
│   └── reminder_watcher.py# Background chron for Push Notifications
└── bot.py                 # Application factory and router registry
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
