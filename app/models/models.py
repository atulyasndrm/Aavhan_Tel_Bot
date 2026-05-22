from datetime import datetime

def create_job_schema(title, date, time, fees, location, job_datetime=None):
    now = datetime.utcnow()
    return {
        "title": title,
        "date": date,
        "time": time,
        "datetime": job_datetime,  # Pass the parsed datetime object here
        "location": location,
        "fees": fees,
        "status": "open",
        "assigned_priest": None,  
        "rejected_by": [],        
        "reminders_sent": [],
        "created_at": now,
        "updated_at": now
    }

def create_user_schema(user_id, name, role="priest", phone=None, document=None, verification_status="pending", verified=False):
    """Schema representation for Priest and Admin users"""
    return {
        "id": user_id,
        "name": name,
        "phone": phone,
        "role": role,
        "verification_status": verification_status,
        "verified": verified,
        "document": document
    }