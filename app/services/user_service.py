from app.db.postgres import db_pool


async def get_user_details(user_id: int):
    """Fetches a single user by their ID."""
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)


async def get_users_details(user_ids: list[int]):
    """Fetches multiple users from a list of IDs."""
    if not user_ids:
        return []
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM users WHERE id = ANY($1::bigint[])", user_ids)

async def get_all_users_for_report():
    """Fetches all users for the admin PDF report."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM users 
            ORDER BY verification_status, created_at DESC
        """)

async def search_priests(query_str: str, limit: int = 5, offset: int = 0):
    """Searches priests by name, phone, or ID."""
    search_pattern = f"%{query_str}%"
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM users 
            WHERE (id::text ILIKE $1) OR (name ILIKE $1) OR (phone ILIKE $1)
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """, search_pattern, limit, offset)

async def get_top_priests(limit: int = 10):
    """Fetches the top priests ranked by the number of completed jobs."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT u.id, u.name, u.phone, COUNT(b.id) as completed_jobs 
            FROM users u 
            JOIN bookings b ON u.id = b.assigned_priest 
            WHERE b.status = 'completed' AND u.verified = TRUE
            GROUP BY u.id, u.name, u.phone
            ORDER BY completed_jobs DESC 
            LIMIT $1
        """, limit)