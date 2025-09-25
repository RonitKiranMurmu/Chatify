#!/usr/bin/env python3
"""
Script to fix double-encrypted messages in MongoDB and blockchain
"""
import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from cryptography.fernet import Fernet
import json
import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MONGO_URI = "mongodb+srv://madfuryalpha:FuryAlpha123@peerpulse.tqwqyvp.mongodb.net/"
DATABASE_NAME = "peerpulse"
MESSAGE_COLLECTION = "messages"
BLOCKS_COLLECTION = "blocks"
ENCRYPTION_KEY = "XpjqYtM-yjvwu3-JfJR0OqqjOwrdkVj-KlVmnXMkmw8"

def get_fernet():
    """Get Fernet encryption instance"""
    key_bytes = base64.urlsafe_b64decode(ENCRYPTION_KEY.encode() + b'==')
    return Fernet(key_bytes)

def is_double_encrypted(message):
    """Check if a message appears to be double encrypted"""
    try:
        # Try to decrypt once
        fernet = get_fernet()
        decrypted = fernet.decrypt(message.encode()).decode()
        
        # If the result still looks like base64 encrypted data, it's double encrypted
        if len(decrypted) > 20 and all(c.isalnum() or c in '+/=' for c in decrypted.replace('-', '+').replace('_', '/')):
            return True, decrypted
        return False, None
    except Exception:
        return False, None

def fix_database_messages():
    """Fix double-encrypted messages in MongoDB"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        messages_collection = db[MESSAGE_COLLECTION]
        blocks_collection = db[BLOCKS_COLLECTION]
        
        logger.info("Connected to MongoDB")
        
        # Find all messages in messages collection
        messages = list(messages_collection.find({}))
        logger.info(f"Found {len(messages)} messages to check")
        
        fixed_count = 0
        for msg in messages:
            if 'message' in msg:
                is_double, single_encrypted = is_double_encrypted(msg['message'])
                if is_double and single_encrypted:
                    # Update with single-encrypted version
                    messages_collection.update_one(
                        {'_id': msg['_id']},
                        {'$set': {'message': single_encrypted}}
                    )
                    fixed_count += 1
                    logger.info(f"Fixed double-encrypted message: {msg['_id']}")
        
        # Check blockchain blocks collection
        blocks = list(blocks_collection.find({}))
        logger.info(f"Found {len(blocks)} blocks to check")
        
        for block in blocks:
            for tx in block.get('transactions', []):
                if 'message' in tx:
                    is_double, single_encrypted = is_double_encrypted(tx['message'])
                    if is_double and single_encrypted:
                        # Update the block with fixed transaction
                        blocks_collection.update_one(
                            {'_id': block['_id'], 'transactions.message': tx['message']},
                            {'$set': {'transactions.$.message': single_encrypted}}
                        )
                        fixed_count += 1
                        logger.info(f"Fixed double-encrypted blockchain transaction in block: {block['_id']}")
        
        logger.info(f"Fixed {fixed_count} double-encrypted messages in database")
        client.close()
        return fixed_count
        
    except Exception as e:
        logger.error(f"Error fixing database messages: {e}")
        return 0

def fix_blockchain_file():
    """Fix double-encrypted messages in blockchain.json"""
    blockchain_file = "blockchain.json"
    if not os.path.exists(blockchain_file):
        logger.warning("blockchain.json not found")
        return 0
    
    try:
        with open(blockchain_file, 'r') as f:
            blockchain_data = json.load(f)
        
        fixed_count = 0
        for block in blockchain_data.get('chain', []):
            for tx in block.get('transactions', []):
                if 'message' in tx:
                    is_double, single_encrypted = is_double_encrypted(tx['message'])
                    if is_double and single_encrypted:
                        tx['message'] = single_encrypted
                        fixed_count += 1
                        logger.info(f"Fixed double-encrypted blockchain transaction")
        
        # Save the fixed blockchain
        with open(blockchain_file, 'w') as f:
            json.dump(blockchain_data, f, indent=2)
        
        logger.info(f"Fixed {fixed_count} double-encrypted messages in blockchain")
        return fixed_count
        
    except Exception as e:
        logger.error(f"Error fixing blockchain messages: {e}")
        return 0

if __name__ == "__main__":
    logger.info("Starting double-encryption fix...")
    
    db_fixed = fix_database_messages()
    blockchain_fixed = fix_blockchain_file()
    
    logger.info(f"Fix complete!")
    logger.info(f"Database messages fixed: {db_fixed}")
    logger.info(f"Blockchain messages fixed: {blockchain_fixed}")
    
    if db_fixed == 0 and blockchain_fixed == 0:
        logger.info("No double-encrypted messages found - your data is clean!")