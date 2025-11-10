"""
Database models for Chatify
"""
from datetime import datetime
from app.utils.database import get_collection


class User:
    """User model"""
    
    collection = 'users'
    
    @staticmethod
    def create(username, password_hash, identity_pub, signed_prekey_pub, signed_prekey_sig, one_time_prekeys):
        """
        Create a new user
        
        Args:
            username: Unique username
            password_hash: Hashed password
            identity_pub: Public identity key (base64)
            signed_prekey_pub: Public signed prekey (base64)
            signed_prekey_sig: Signature of signed prekey (base64)
            one_time_prekeys: List of one-time prekeys
        
        Returns:
            Inserted user ID
        """
        user_data = {
            'username': username,
            'password_hash': password_hash,
            'identity_pub': identity_pub,
            'signed_prekey_pub': signed_prekey_pub,
            'signed_prekey_sig': signed_prekey_sig,
            'one_time_prekeys': one_time_prekeys,
            'created_at': datetime.utcnow(),
            'last_seen': datetime.utcnow(),
            'is_online': False
        }
        
        result = get_collection(User.collection).insert_one(user_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_username(username):
        """Find user by username"""
        return get_collection(User.collection).find_one({'username': username})
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        from bson import ObjectId
        return get_collection(User.collection).find_one({'_id': ObjectId(user_id)})
    
    @staticmethod
    def get_all_users(exclude_username=None):
        """Get all users except specified one"""
        query = {}
        if exclude_username:
            query['username'] = {'$ne': exclude_username}
        return list(get_collection(User.collection).find(
            query,
            {'password_hash': 0}  # Exclude password hash
        ))
    
    @staticmethod
    def update_online_status(username, is_online):
        """Update user's online status"""
        get_collection(User.collection).update_one(
            {'username': username},
            {
                '$set': {
                    'is_online': is_online,
                    'last_seen': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def get_public_keys(username):
        """Get user's public keys for key exchange"""
        user = get_collection(User.collection).find_one(
            {'username': username},
            {
                'identity_pub': 1,
                'signed_prekey_pub': 1,
                'signed_prekey_sig': 1,
                'one_time_prekeys': 1
            }
        )
        return user
    
    @staticmethod
    def consume_one_time_prekey(username):
        """
        Get and mark one one-time prekey as used
        
        Returns:
            One-time prekey or None if none available
        """
        user = get_collection(User.collection).find_one_and_update(
            {'username': username, 'one_time_prekeys.used': False},
            {'$set': {'one_time_prekeys.$.used': True}},
            projection={'one_time_prekeys.$': 1}
        )
        
        if user and 'one_time_prekeys' in user:
            return user['one_time_prekeys'][0]
        return None
    
    @staticmethod
    def add_one_time_prekeys(username, new_prekeys):
        """Add new one-time prekeys for user"""
        get_collection(User.collection).update_one(
            {'username': username},
            {'$push': {'one_time_prekeys': {'$each': new_prekeys}}}
        )


class Message:
    """Message model"""
    
    collection = 'messages'
    
    @staticmethod
    def create(chat_id, sender, recipient, ciphertext, nonce, ephemeral_pub, msg_type='text', metadata=None, chat_type='private', group_id=None):
        """
        Create a new message
        
        Args:
            chat_id: Unique chat identifier
            sender: Sender username
            recipient: Recipient username (or group ID for group messages)
            ciphertext: Encrypted message content (base64)
            nonce: Encryption nonce (base64)
            ephemeral_pub: Ephemeral public key (base64)
            msg_type: Message type (text, file, media)
            metadata: Additional metadata dict
            chat_type: 'private' or 'group'
            group_id: Group ID if chat_type is 'group'
        
        Returns:
            Inserted message ID
        """
        message_data = {
            'chat_id': chat_id,
            'sender': sender,
            'recipient': recipient,
            'ciphertext': ciphertext,
            'nonce': nonce,
            'ephemeral_pub': ephemeral_pub,
            'timestamp': datetime.utcnow(),
            'type': msg_type,
            'chat_type': chat_type,
            'metadata': metadata or {
                'read': False,
                'delivered': False,
                'reactions': [],
                'reply_to': None,
                'edited': False
            }
        }
        
        # Add group_id if this is a group message
        if chat_type == 'group' and group_id:
            message_data['group_id'] = group_id
        
        result = get_collection(Message.collection).insert_one(message_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_chat_history(chat_id, limit=50, skip=0):
        """Get chat history for a chat"""
        return list(get_collection(Message.collection).find(
            {'chat_id': chat_id}
        ).sort('timestamp', -1).skip(skip).limit(limit))
    
    @staticmethod
    def mark_as_read(message_id):
        """Mark message as read"""
        from bson import ObjectId
        get_collection(Message.collection).update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'metadata.read': True}}
        )
    
    @staticmethod
    def mark_as_delivered(message_id):
        """Mark message as delivered"""
        from bson import ObjectId
        get_collection(Message.collection).update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'metadata.delivered': True}}
        )
    
    @staticmethod
    def add_reaction(message_id, username, emoji):
        """Add reaction to message"""
        from bson import ObjectId
        get_collection(Message.collection).update_one(
            {'_id': ObjectId(message_id)},
            {'$push': {'metadata.reactions': {'user': username, 'emoji': emoji}}}
        )
    
    @staticmethod
    def find_by_id(message_id):
        """Find message by ID"""
        from bson import ObjectId
        return get_collection(Message.collection).find_one({'_id': ObjectId(message_id)})
    
    @staticmethod
    def delete_message(message_id):
        """Mark a message as deleted instead of removing it"""
        from bson import ObjectId
        get_collection(Message.collection).update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'metadata.deleted': True, 'deleted_at': datetime.utcnow()}}
        )
    
    @staticmethod
    def get_unread_counts(username):
        """Get unread message counts per chat for a user"""
        pipeline = [
            # Match messages where user is recipient and message is unread
            {
                '$match': {
                    'recipient': username,
                    'metadata.read': False
                }
            },
            # Group by sender (chat partner)
            {
                '$group': {
                    '_id': '$sender',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        results = list(get_collection(Message.collection).aggregate(pipeline))
        
        # Convert to dict: {sender: count}
        unread_counts = {item['_id']: item['count'] for item in results}
        return unread_counts


class Group:
    """Group model"""
    
    collection = 'groups'
    
    @staticmethod
    def create(group_name, admin, members, group_key_encrypted):
        """
        Create a new group
        
        Args:
            group_name: Name of the group
            admin: Admin username
            members: List of member usernames
            group_key_encrypted: Dict of {username: encrypted_group_key}
        
        Returns:
            Inserted group ID
        """
        group_data = {
            'group_name': group_name,
            'admin': admin,
            'members': members,
            'group_key_encrypted': group_key_encrypted,
            'created_at': datetime.utcnow()
        }
        
        result = get_collection(Group.collection).insert_one(group_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(group_id):
        """Find group by ID"""
        from bson import ObjectId
        return get_collection(Group.collection).find_one({'_id': ObjectId(group_id)})
    
    @staticmethod
    def get_user_groups(username):
        """Get all groups user is member of"""
        return list(get_collection(Group.collection).find(
            {'members': username}
        ))
    
    @staticmethod
    def add_member(group_id, username, encrypted_group_key):
        """Add member to group (restore old key if they were previously removed)"""
        from bson import ObjectId
        
        # Check if this user was previously a member (has a backed up key)
        group = get_collection(Group.collection).find_one({'_id': ObjectId(group_id)})
        removed_keys = group.get('removed_members_keys', {}) if group else {}
        
        if username in removed_keys:
            # User was previously a member - restore their original key
            old_encrypted_key = removed_keys[username]
            
            # Remove from removed_members_keys and add back to members with original key
            get_collection(Group.collection).update_one(
                {'_id': ObjectId(group_id)},
                {
                    '$push': {'members': username},
                    '$set': {f'group_key_encrypted.{username}': old_encrypted_key},
                    '$unset': {f'removed_members_keys.{username}': ''}
                }
            )
        else:
            # New member - use provided encrypted key
            get_collection(Group.collection).update_one(
                {'_id': ObjectId(group_id)},
                {
                    '$push': {'members': username},
                    '$set': {f'group_key_encrypted.{username}': encrypted_group_key}
                }
            )
    
    @staticmethod
    def remove_member(group_id, username):
        """Remove member from group and backup their key"""
        from bson import ObjectId
        
        # Get current group to backup the member's key
        group = get_collection(Group.collection).find_one({'_id': ObjectId(group_id)})
        if group and username in group.get('group_key_encrypted', {}):
            # Store the removed member's key in a backup field
            removed_keys = group.get('removed_members_keys', {})
            removed_keys[username] = group['group_key_encrypted'][username]
            
            get_collection(Group.collection).update_one(
                {'_id': ObjectId(group_id)},
                {
                    '$pull': {'members': username},
                    '$unset': {f'group_key_encrypted.{username}': ''},
                    '$set': {'removed_members_keys': removed_keys}
                }
            )
        else:
            # Fallback if no key found
            get_collection(Group.collection).update_one(
                {'_id': ObjectId(group_id)},
                {
                    '$pull': {'members': username},
                    '$unset': {f'group_key_encrypted.{username}': ''}
                }
            )
    
    @staticmethod
    def update_group_keys(group_id, new_group_key_encrypted):
        """Update group keys (for key rotation)"""
        from bson import ObjectId
        get_collection(Group.collection).update_one(
            {'_id': ObjectId(group_id)},
            {'$set': {'group_key_encrypted': new_group_key_encrypted}}
        )


class ServerChat:
    """Server-wide chat model (public chat room)"""
    
    collection = 'server_messages'
    
    @staticmethod
    def create(sender, message_text):
        """
        Create a new server chat message (no encryption)
        
        Args:
            sender: Sender username
            message_text: Plain text message (not encrypted)
        
        Returns:
            Inserted message document
        """
        message_data = {
            'sender': sender,
            'message': message_text,
            'timestamp': datetime.utcnow(),
            'reactions': {}  # Format: {emoji: [usernames]}
        }
        
        result = get_collection(ServerChat.collection).insert_one(message_data)
        message_data['_id'] = result.inserted_id
        return message_data
    
    @staticmethod
    def get_recent_messages(limit=50):
        """Get recent server chat messages"""
        return list(get_collection(ServerChat.collection).find()
                   .sort('timestamp', -1)
                   .limit(limit))
    
    @staticmethod
    def add_reaction(message_id, username, emoji):
        """Add reaction to server message"""
        from bson import ObjectId
        
        # Get current reactions
        message = get_collection(ServerChat.collection).find_one({'_id': ObjectId(message_id)})
        if not message:
            return
        
        reactions = message.get('reactions', {})
        
        # Toggle reaction
        if emoji in reactions:
            if username in reactions[emoji]:
                reactions[emoji].remove(username)
                if not reactions[emoji]:
                    del reactions[emoji]
            else:
                reactions[emoji].append(username)
        else:
            reactions[emoji] = [username]
        
        # Update in database
        get_collection(ServerChat.collection).update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'reactions': reactions}}
        )
    
    @staticmethod
    def delete_message(message_id):
        """Mark server message as deleted"""
        from bson import ObjectId
        get_collection(ServerChat.collection).update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'deleted': True, 'deleted_at': datetime.utcnow()}}
        )
