import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI


client = AsyncIOMotorClient(
    MONGO_URI, 
    tlsCAFile=certifi.where(),
    tlsAllowInvalidCertificates=True  # Bypasses strict SSL validation
)
db = client["aavhan"]

users_col=db["users"]
jobs_col = db["jobs"]
