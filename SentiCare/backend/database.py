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
        
        cls.client = AsyncIOMotorClient(mongodb_uri)
        print("Connected to MongoDB Atlas")
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            print("Closed MongoDB connection")
    
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
