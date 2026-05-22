import asyncio
import json
from datetime import datetime
from app.db.postgres import db_pool
from app.services.broadcast import broadcast_job


sent_jobs = set()

async def watch_jobs(app):
    conn = await db_pool.acquire()
    
    async def handle_notification(connection, pid, channel, payload):
        job = json.loads(payload)
        job_id = str(job["id"])

        if job_id in sent_jobs:
            return

        sent_jobs.add(job_id)
        print("🔥 New job detected:", job_id)

        # Re-convert iso strings back to datetime objects to maintain feature consistency
        if job.get("datetime"):
            job["datetime"] = datetime.fromisoformat(job["datetime"])

        await broadcast_job(app, job)

    await conn.add_listener('new_job_channel', handle_notification)
    
    # Keep this connection alive to listen forever
    while True:
        await asyncio.sleep(3600)