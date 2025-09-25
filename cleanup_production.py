#!/usr/bin/env python3
"""
Production MongoDB cleanup script for DecentralizedChat
This script clears old encrypted messages from MongoDB Atlas production database.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_production_db():
    """Clear old encrypted messages from the production database"""
    
    # Get production MongoDB connection details
    MONGO_URI = os.environ.get("MONGO_URI")
    MONGO_DB = os.environ.get("MONGO_DB", "chatify_dev")
    
    if not MONGO_URI:
        print("❌ Error: MONGO_URI environment variable not set!")
        print("   Please set your MongoDB Atlas connection string in .env file")
        return
    
    print(f"🚀 Production Database Cleanup")
    print(f"Database: {MONGO_DB}")
    print(f"URI: {MONGO_URI[:30]}..." if len(MONGO_URI) > 30 else f"URI: {MONGO_URI}")
    
    try:
        # Connect to MongoDB Atlas
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
        
        db = mongo_client[MONGO_DB]
        messages_col = db["messages"]
        blocks_col = db["blocks"]
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        
        # Count existing documents
        message_count = messages_col.count_documents({})
        block_count = blocks_col.count_documents({})
        
        print(f"\n📊 Production database status:")
        print(f"   Messages: {message_count}")
        print(f"   Blocks: {block_count}")
        
        if message_count == 0 and block_count == 0:
            print("\n✅ Production database is already clean!")
            return
        
        # Show some sample encrypted messages
        if message_count > 0:
            print(f"\n🔍 Sample messages (showing first 3):")
            sample_messages = messages_col.find({}).limit(3)
            for i, msg in enumerate(sample_messages, 1):
                content = msg.get('content', '')
                preview = content[:50] + "..." if len(content) > 50 else content
                print(f"   {i}. {preview}")
        
        # Ask for confirmation
        print(f"\n⚠️  WARNING: This will delete ALL {message_count} messages and {block_count} blocks from PRODUCTION!")
        print(f"   This action cannot be undone.")
        response = input(f"\n   Type 'DELETE PRODUCTION DATA' to confirm: ")
        
        if response == 'DELETE PRODUCTION DATA':
            # Clear old messages and blocks
            result_messages = messages_col.delete_many({})
            result_blocks = blocks_col.delete_many({})
            
            print(f"\n🧹 Production cleanup completed!")
            print(f"   Deleted {result_messages.deleted_count} messages")
            print(f"   Deleted {result_blocks.deleted_count} blocks")
            print(f"\n✅ Production database is now clean and ready for new encrypted messages!")
        else:
            print("\n❌ Production cleanup cancelled. Exact phrase required for safety.")
            
    except Exception as e:
        print(f"\n❌ Error connecting to production database: {e}")
        
    finally:
        try:
            mongo_client.close()
        except:
            pass

if __name__ == "__main__":
    cleanup_production_db()