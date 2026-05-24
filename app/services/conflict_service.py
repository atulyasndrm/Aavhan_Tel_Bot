from datetime import timedelta
from app.db.postgres import db_pool

# A standard duration for pujas, used to calculate time conflicts.
# For a more advanced system, this could be a field in the job document itself.
PUJA_DURATION_HOURS = 3


async def has_conflict(priest_id, job_datetime):
    """
    Checks if the priest has another assigned job that conflicts with the new one.

    A conflict exists if the time windows of two jobs overlap. We assume a
    fixed duration for each puja to calculate its time window.
    """
    
    # The end time of the new job, assuming a fixed duration.
    new_job_end_time = job_datetime + timedelta(hours=PUJA_DURATION_HOURS)
    
    # Use PostgreSQL to check if there is any overlapping assigned job.
    # Overlap formula: existing_start < new_end AND new_start < existing_end
    async with db_pool.acquire() as conn:
        conflict = await conn.fetchrow("""
            SELECT id FROM bookings 
            WHERE assigned_priest = $1 AND status = 'assigned'
            AND datetime < $2 
            AND $3 < (datetime + interval '3 hours')
        """, priest_id, new_job_end_time, job_datetime)

    return conflict is not None