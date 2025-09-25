#!/usr/bin/env python3
"""
MongoDB cleanup script for DecentralizedChat
This script clears old encrypted messages to start fresh with the new encryption system.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_old_messages():
    """Clear old encrypted messages from the database"""
    
    # Get MongoDB connection details
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
    MONGO_DB = os.environ.get("MONGO_DB", "peerpulse")
    
    print(f"Connecting to MongoDB: {MONGO_DB}")
    print(f"URI: {MONGO_URI[:20]}..." if len(MONGO_URI) > 20 else f"URI: {MONGO_URI}")
    
    try:
        # Connect to MongoDB
        is_atlas = MONGO_URI.startswith("mongodb+srv://") or "atlas" in MONGO_URI.lower()
        
        if is_atlas:
            mongo_client = MongoClient(
                MONGO_URI,
                maxPoolSize=50,
                retryWrites=True,
                retryReads=True,
                connectTimeoutMS=10000,
                serverSelectionTimeoutMS=10000,
                tls=True,
                tlsAllowInvalidCertificates=False
            )
        else:
            mongo_client = MongoClient(
                MONGO_URI,
                maxPoolSize=50,
                retryWrites=True,
                retryReads=True,
                connectTimeoutMS=10000,
                serverSelectionTimeoutMS=10000
            )
        
        db = mongo_client[MONGO_DB]
        messages_col = db["messages"]
        blocks_col = db["blocks"]
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully!")
        
        # Count existing documents
        message_count = messages_col.count_documents({})
        block_count = blocks_col.count_documents({})
        
        print(f"\n📊 Current database status:")
        print(f"   Messages: {message_count}")
        print(f"   Blocks: {block_count}")
        
        if message_count == 0 and block_count == 0:
            print("\n✅ Database is already clean!")
            return
        
        # Ask for confirmation
        response = input(f"\n⚠️  This will delete {message_count} messages and {block_count} blocks. Continue? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            # Clear old messages and blocks
            result_messages = messages_col.delete_many({})
            result_blocks = blocks_col.delete_many({})
            
            print(f"\n🧹 Cleanup completed!")
            print(f"   Deleted {result_messages.deleted_count} messages")
            print(f"   Deleted {result_blocks.deleted_count} blocks")
            print(f"\n✅ Database is now clean and ready for new encrypted messages!")
        else:
            print("\n❌ Cleanup cancelled.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        try:
            mongo_client.close()
        except:
            pass

if __name__ == "__main__":
    print("🚀 DecentralizedChat Database Cleanup")
    print("=====================================")
    cleanup_old_messages()