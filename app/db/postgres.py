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
    db_pool.pool = await asyncpg.create_pool(DATABASE_URL, statement_cache_size=0)
    
    async with db_pool.acquire() as conn:
        # Ensure UUID helper exists for gen_random_uuid()
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        # Create Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                role TEXT DEFAULT 'priest',
                verification_status TEXT DEFAULT 'pending',
                verified BOOLEAN DEFAULT FALSE,
                document TEXT,
                doc_type TEXT DEFAULT 'document',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create Bookings table (Using UUID for ID generation)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT,
                host_name TEXT,
                host_mobile TEXT,
                host_email TEXT,
                date TEXT,
                time TEXT,
                datetime TIMESTAMP,
                venue TEXT,
                city TEXT,
                state TEXT,
                samagri TEXT,
                notes TEXT,
                location TEXT,
                fees TEXT,
                status TEXT DEFAULT 'open',
                assigned_priest BIGINT,
                rejected_by BIGINT[] DEFAULT '{}',
                broadcast_messages JSONB DEFAULT '[]'::jsonb,
                reminders_sent TEXT[] DEFAULT '{}',
                broadcast_status TEXT DEFAULT 'pending',
                broadcast_attempts INT DEFAULT 0,
                broadcast_last_attempt_at TIMESTAMP,
                next_broadcast_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                broadcast_last_error TEXT,
                broadcasted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Auto-migrate new columns if the table already existed from an older version
        await conn.execute("""
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS title TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS datetime TIMESTAMP;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS location TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS fees TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS host_name TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS host_mobile TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS host_email TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS venue TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS city TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS state TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS samagri TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS notes TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS assigned_priest BIGINT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS rejected_by BIGINT[] DEFAULT '{}';
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS broadcast_messages JSONB DEFAULT '[]'::jsonb;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reminders_sent TEXT[] DEFAULT '{}';
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS broadcast_status TEXT DEFAULT 'pending';
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS broadcast_attempts INT DEFAULT 0;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS broadcast_last_attempt_at TIMESTAMP;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS next_broadcast_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS broadcast_last_error TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS broadcasted_at TIMESTAMP;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS full_name TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS mobile TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS email TEXT;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS ceremony_type TEXT;
            
            ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS doc_type TEXT DEFAULT 'document';
        """)
        
        # Create Trigger for LISTEN/NOTIFY (Replaces MongoDB Change Streams)
        await conn.execute("""
            CREATE OR REPLACE FUNCTION notify_new_job() RETURNS TRIGGER AS $$
            BEGIN
                PERFORM pg_notify('new_job_channel', row_to_json(NEW)::text);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS job_insert_trigger ON bookings;
            CREATE TRIGGER job_insert_trigger AFTER INSERT ON bookings
            FOR EACH ROW EXECUTE FUNCTION notify_new_job();
        """)
        
        # Create a trigger to ensure Website data matches Bot expectations
        await conn.execute("""
            CREATE OR REPLACE FUNCTION format_website_booking() RETURNS TRIGGER AS $$
            BEGIN
                -- 1. Map website status 'new' to bot status 'open'
                IF NEW.status = 'new' THEN
                    NEW.status := 'open';
                END IF;

                -- 2. Map website column names to bot column names
                IF NEW.title IS NULL THEN NEW.title := NEW.ceremony_type; END IF;
                IF NEW.host_name IS NULL THEN NEW.host_name := NEW.full_name; END IF;
                IF NEW.host_mobile IS NULL THEN NEW.host_mobile := NEW.mobile; END IF;
                IF NEW.host_email IS NULL THEN NEW.host_email := NEW.email; END IF;

                -- 3. Construct datetime for the bot's conflict management
                IF NEW.datetime IS NULL AND NEW.date IS NOT NULL AND NEW.time IS NOT NULL THEN
                    NEW.datetime := (NEW.date::text || ' ' || NEW.time::text)::timestamp;
                END IF;

                -- 4. Set location fallback
                IF NEW.location IS NULL THEN
                    NEW.location := COALESCE(NEW.venue, COALESCE(NEW.city, 'Yajman House'));
                END IF;
                
                -- 5. Ensure required arrays aren't NULL for bot queries
                IF NEW.rejected_by IS NULL THEN NEW.rejected_by := '{}'; END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS format_website_trigger ON bookings;
            CREATE TRIGGER format_website_trigger BEFORE INSERT ON bookings
            FOR EACH ROW EXECUTE FUNCTION format_website_booking();
        """)
        
        # Drop the old jobs table as it has been replaced by bookings
        await conn.execute("DROP TABLE IF EXISTS jobs;")