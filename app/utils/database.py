"""
Database utility module for MongoDB operations
"""
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
import logging

# Global MongoDB client and database
_client = None
_db = None

logger = logging.getLogger(__name__)

def init_db(mongodb_uri):
    """
    Initialize MongoDB connection
    
    Args:
        mongodb_uri: MongoDB connection string
    
    Returns:
        Database instance
    """
    global _client, _db
    
    try:
        _client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Test connection
        _client.admin.command('ping')
        
        # Get database name from URI or use default
        db_name = mongodb_uri.split('/')[-1].split('?')[0] or 'chatify'
        _db = _client[db_name]
        
        logger.info(f"Connected to MongoDB database: {db_name}")
        
        # Create indexes
        create_indexes()
        
        return _db
        
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise Exception(f"Database connection failed: {e}")


def get_db():
    """
    Get the current database instance
    
    Returns:
        Database instance
    """
    if _db is None:
        raise Exception("Database not initialized. Call init_db() first.")
    return _db


def create_indexes():
    """Create database indexes for better performance"""
    db = get_db()
    
    # Users collection indexes
    db.users.create_index('username', unique=True)
    db.users.create_index('created_at')
    db.users.create_index('is_online')  # For faster online user queries
    
    # Messages collection indexes (optimized for performance)
    db.messages.create_index([('chat_id', 1), ('timestamp', -1)])  # Main query pattern
    db.messages.create_index([('recipient', 1), ('metadata.read', 1)])  # Unread messages query
    db.messages.create_index('sender')
    db.messages.create_index('recipient')
    db.messages.create_index('timestamp')  # For time-based queries
    
    # Groups collection indexes
    db.groups.create_index('group_name')
    db.groups.create_index('admin')
    db.groups.create_index('members')
    
    # Server messages collection indexes
    db.server_messages.create_index([('timestamp', -1)])  # For recent messages query
    db.server_messages.create_index('sender')
    
    # Sessions collection indexes
    db.sessions.create_index('user_id')
    db.sessions.create_index('expires_at')
    
    logger.info("Database indexes created successfully")


def close_db():
    """Close database connection"""
    global _client
    if _client:
        _client.close()
        logger.info("Database connection closed")


# Collection helper functions
def get_collection(collection_name):
    """
    Get a specific collection
    
    Args:
        collection_name: Name of the collection
    
    Returns:
        Collection instance
    """
    return get_db()[collection_name]
