from app.db.postgres import db_pool

async def is_verified(user_id):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT verified FROM users WHERE id = $1", str(user_id))
    return user and user.get("verified")