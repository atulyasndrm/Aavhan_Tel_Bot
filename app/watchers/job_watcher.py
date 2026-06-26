import asyncio
import json
import logging
from datetime import datetime, timezone

import asyncpg
from config import DATABASE_URL, logger
from app.db.postgres import db_pool
from app.services.broadcast import broadcast_job


def retry_delay(attempts: int) -> int:
    return min(300, 5 * (2 ** max(0, attempts - 1)))


async def claim_pending_job(job_id):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            """
                UPDATE bookings
                SET broadcast_status = 'processing',
                    broadcast_attempts = broadcast_attempts + 1,
                    broadcast_last_attempt_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1::uuid
                  AND broadcast_status IN ('pending', 'failed')
                  AND status IN ('new', 'pending')
                  AND next_broadcast_at <= NOW()
                RETURNING *
            """,
            job_id
        )


async def schedule_retry(job_id: str, last_error: str, attempts: int):
    delay_seconds = retry_delay(attempts)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
                UPDATE bookings
                SET broadcast_status = 'failed',
                    broadcast_last_error = $2,
                    next_broadcast_at = NOW() + ($3 || ' seconds')::interval,
                    updated_at = NOW()
                WHERE id = $1::uuid
            """,
            job_id,
            last_error[:1000],
            str(delay_seconds)
        )


async def mark_job_broadcasted(job_id: str):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
                UPDATE bookings
                SET broadcast_status = 'done',
                    broadcasted_at = NOW(),
                    next_broadcast_at = NULL,
                    updated_at = NOW()
                WHERE id = $1::uuid
            """,
            job_id
        )


async def sync_pending_jobs(app):
    async with db_pool.acquire() as conn:
        jobs = await conn.fetch("""
                SELECT id, broadcast_status, status, next_broadcast_at, created_at
                FROM bookings
                WHERE broadcast_status IN ('pending', 'failed')
                  AND status IN ('new', 'pending')
                  AND next_broadcast_at <= NOW()
                ORDER BY created_at ASC
                LIMIT 20
            """)

    for job in jobs:
        await process_job(str(job["id"]), app)


async def process_job(job_id: str, app):
    row = await claim_pending_job(job_id)
    if not row:
        return

    job = dict(row)
    logger.info("New job detected: %s", job_id)

    if job.get("datetime"):
        try:
            job["datetime"] = datetime.fromisoformat(job["datetime"])
        except Exception:
            pass

    try:
        await broadcast_job(app, job)
        await mark_job_broadcasted(job_id)
    except Exception as e:
        logger.exception("Error broadcasting job %s", job_id)
        await schedule_retry(job_id, str(e), job.get("broadcast_attempts", 1))


async def watch_jobs(app):
    logger.info("Job watcher starting")

    async def process_payload(payload):
        try:
            job = json.loads(payload)
            await process_job(str(job["id"]), app)
        except Exception as e:
            logger.exception("Failed to parse notification payload")

    def handle_notification(connection, pid, channel, payload):
        asyncio.create_task(process_payload(payload))

    while True:
        conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        try:
            logger.info("Connected to Neon DB listen channel")
            await conn.add_listener('new_job_channel', handle_notification)
            await sync_pending_jobs(app)

            while True:
                await conn.execute("SELECT 1")
                await asyncio.sleep(15)
                await sync_pending_jobs(app)
        except Exception as e:
            logger.warning("Job watcher disconnected, reconnecting in 5s... %s", e)
            await asyncio.sleep(5)
        finally:
            await conn.close()