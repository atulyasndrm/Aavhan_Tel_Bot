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