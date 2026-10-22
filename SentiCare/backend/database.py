from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")
        
        cls.client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=10000)
        try:
            # Motor connects lazily, so ping to verify the connection for real
            await cls.client.admin.command("ping")
        except Exception as e:
            cls.client.close()
            cls.client = None
            print(f"[MongoDB] Connection FAILED: {type(e).__name__}: {e}")
            print("[MongoDB] Check MONGODB_URI in backend/.env and that your IP "
                  "is allowed in MongoDB Atlas Network Access")
            raise
        print(f"[MongoDB] Connected successfully (database: {cls.client.dep_app_db.name})")
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            print("[MongoDB] Connection closed")
    
    @classmethod
    def get_database(cls):
        """Get the database instance"""
        if not cls.client:
            raise RuntimeError("Database not connected")
        return cls.client.dep_app_db
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Get a collection from the database"""
        db = cls.get_database()
        return db[collection_name]

# Convenience functions
async def get_users_collection():
    """Get users collection"""
    return Database.get_collection("users")
