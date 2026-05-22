import asyncpg
from config import DATABASE_URL

class DBPoolProxy:
    def __init__(self):
        self.pool = None

    def __getattr__(self, name):
        if self.pool is None:
            raise AttributeError("Database pool is not initialized yet.")
        return getattr(self.pool, name)

db_pool = DBPoolProxy()

async def init_db():
    # Initialize the connection pool
    db_pool.pool = await asyncpg.create_pool(DATABASE_URL)
    
    async with db_pool.acquire() as conn:
        # Create Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                role TEXT DEFAULT 'priest',
                verification_status TEXT DEFAULT 'pending',
                verified BOOLEAN DEFAULT FALSE,
                document TEXT
            )
        """)
        
        # Create Jobs table (Using UUID for ID generation)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT,
                date TEXT,
                time TEXT,
                datetime TIMESTAMP,
                location TEXT,
                fees TEXT,
                status TEXT DEFAULT 'open',
                assigned_priest BIGINT,
                rejected_by BIGINT[] DEFAULT '{}',
                reminders_sent TEXT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create Trigger for LISTEN/NOTIFY (Replaces MongoDB Change Streams)
        await conn.execute("""
            CREATE OR REPLACE FUNCTION notify_new_job() RETURNS TRIGGER AS $$
            BEGIN
                PERFORM pg_notify('new_job_channel', row_to_json(NEW)::text);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS job_insert_trigger ON jobs;
            CREATE TRIGGER job_insert_trigger AFTER INSERT ON jobs
            FOR EACH ROW EXECUTE FUNCTION notify_new_job();
        """)