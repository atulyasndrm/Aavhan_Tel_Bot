from datetime import datetime
from app.db.postgres import db_pool

async def get_available_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM jobs 
            WHERE status = 'open' 
            AND NOT ($1 = ANY(rejected_by))
            AND datetime > $2
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id, datetime.utcnow())

async def get_applied_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM jobs 
            WHERE assigned_priest = $1 AND status = 'assigned'
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id)

async def get_rejected_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM jobs 
            WHERE $1 = ANY(rejected_by)
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id)

async def get_completed_jobs(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM jobs 
            WHERE assigned_priest = $1 AND status = 'completed'
            ORDER BY created_at DESC 
            LIMIT 20
        """, user_id)

async def get_jobs_by_status(status: str):
    """Fetches all jobs with a given status ('open' or 'assigned')."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM jobs 
            WHERE status = $1
            ORDER BY created_at DESC 
            LIMIT 50
        """, status)

async def get_all_rejected_jobs():
    """Fetches all jobs that have been rejected by at least one priest."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM jobs 
            WHERE rejected_by <> '{}'
            ORDER BY created_at DESC 
            LIMIT 50
        """)