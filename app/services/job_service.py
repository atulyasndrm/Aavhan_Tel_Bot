from datetime import datetime
from app.db.postgres import db_pool

async def get_available_jobs(user_id, limit: int = 20, offset: int = 0):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            WHERE status IN ('open', 'new') 
            AND NOT ($1 = ANY(COALESCE(rejected_by, '{}'::BIGINT[])))
            AND (datetime > $2 OR datetime IS NULL)
            ORDER BY created_at DESC 
            LIMIT $3 OFFSET $4
        """, user_id, datetime.utcnow(), limit, offset)

async def get_applied_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            WHERE assigned_priest = $1 AND status = 'assigned'
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id)

async def get_rejected_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            WHERE $1 = ANY(rejected_by)
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id)

async def get_completed_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            WHERE assigned_priest = $1 AND status = 'completed'
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id)

async def get_jobs_by_status(status: str, limit: int = 50, offset: int = 0):
    """Fetches all jobs with a given status ('open' or 'assigned')."""
    async with db_pool.acquire() as conn:
        if status == 'open':
            return await conn.fetch("""
                SELECT * FROM bookings 
                WHERE status IN ('open', 'new')
                ORDER BY created_at DESC 
                LIMIT $1 OFFSET $2
            """, limit, offset)
        else:
            return await conn.fetch("""
                SELECT * FROM bookings 
                WHERE status = $1
                ORDER BY created_at DESC 
                LIMIT $2 OFFSET $3
            """, status, limit, offset)

async def get_all_rejected_jobs(limit: int = 50, offset: int = 0):
    """Fetches all jobs that have been rejected by at least one priest."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            WHERE rejected_by <> '{}'
            ORDER BY created_at DESC 
            LIMIT $1 OFFSET $2
        """, limit, offset)

async def get_expired_unassigned_jobs(limit: int = 50, offset: int = 0):
    """Fetches jobs that are open/new but their datetime has already passed."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            WHERE status IN ('open', 'new')
            AND datetime < $1
            ORDER BY datetime DESC 
            LIMIT $2 OFFSET $3
        """, datetime.utcnow(), limit, offset)

async def get_all_jobs_for_report():
    """Fetches all jobs for the admin PDF report."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM bookings 
            ORDER BY status, created_at DESC
        """)