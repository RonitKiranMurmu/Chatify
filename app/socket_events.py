"""
Socket.IO event handlers for real-time communication
"""
from flask import session, request
from flask_socketio import emit, join_room, leave_room, disconnect
from app.models import Message, User
import logging

logger = logging.getLogger(__name__)

# Store active socket connections
active_users = {}  # {username: socket_id}


def register_events(socketio):
    """Register all Socket.IO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        if 'username' not in session:
            logger.warning("Unauthorized connection attempt")
            disconnect()
            return False
        
        username = session['username']
        active_users[username] = request.sid
        
        # Update user's online status
        User.update_online_status(username, True)
        
        # Broadcast user came online
        emit('user_status', {
            'username': username,
            'status': 'online'
        }, broadcast=True)
        
        logger.info(f"User {username} connected with SID {request.sid}")
    
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if 'username' not in session:
            return
        
        username = session['username']
        
        # Remove from active users
        if username in active_users:
            del active_users[username]
        
        # Update user's offline status
        User.update_online_status(username, False)
        
        # Broadcast user went offline
        emit('user_status', {
            'username': username,
            'status': 'offline'
        }, broadcast=True)
        
        logger.info(f"User {username} disconnected")
    
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Handle sending encrypted message
        
        Data:
            {
                'chat_id': 'user1_user2',
                'recipient': 'username',
                'ciphertext': '...',
                'nonce': '...',
                'ephemeral_pub': '...',
                'type': 'text',
                'metadata': {...}
            }
        """
        if 'username' not in session:
            emit('error', {'message': 'Not authenticated'})
            return
        
        sender = session['username']
        recipient = data.get('recipient')
        chat_id = data.get('chat_id')
        ciphertext = data.get('ciphertext')
        nonce = data.get('nonce')
        ephemeral_pub = data.get('ephemeral_pub')
        msg_type = data.get('type', 'text')
        metadata = data.get('metadata', {})
        
        # Validate data
        if not all([chat_id, recipient, ciphertext, nonce]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        try:
            # Store message in database
            message_id = Message.create(
                chat_id=chat_id,
                sender=sender,
                recipient=recipient,
                ciphertext=ciphertext,
                nonce=nonce,
                ephemeral_pub=ephemeral_pub,
                msg_type=msg_type,
                metadata=metadata
            )
            
            # Prepare message for delivery
            message_data = {
                'message_id': message_id,
                'chat_id': chat_id,
                'sender': sender,
                'recipient': recipient,
                'ciphertext': ciphertext,
                'nonce': nonce,
                'ephemeral_pub': ephemeral_pub,
                'type': msg_type,
                'metadata': metadata,
                'timestamp': data.get('timestamp')
            }
            
            # Send to recipient if online
            if recipient in active_users:
                socketio.emit('receive_message', message_data, 
                            room=active_users[recipient])
                # Mark as delivered since recipient is online
                Message.mark_as_delivered(message_id)
                
                # Notify sender that message was delivered
                if sender in active_users:
                    socketio.emit('message_status_update', {
                        'message_id': message_id,
                        'status': 'delivered'
                    }, room=active_users[sender])
            
            # Send confirmation to sender
            emit('message_sent', {
                'message_id': message_id,
                'chat_id': chat_id,
                'status': 'delivered' if recipient in active_users else 'sent',
                'timestamp': data.get('timestamp')
            })
            
            logger.info(f"Message from {sender} to {recipient}: {message_id}")
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            emit('error', {'message': 'Failed to send message'})
    
    
    @socketio.on('typing_start')
    def handle_typing_start(data):
        """Handle typing indicator start"""
        if 'username' not in session:
            return
        
        sender = session['username']
        recipient = data.get('recipient')
        
        if recipient and recipient in active_users:
            socketio.emit('user_typing', {
                'username': sender,
                'typing': True
            }, room=active_users[recipient])
    
    
    @socketio.on('typing_stop')
    def handle_typing_stop(data):
        """Handle typing indicator stop"""
        if 'username' not in session:
            return
        
        sender = session['username']
        recipient = data.get('recipient')
        
        if recipient and recipient in active_users:
            socketio.emit('user_typing', {
                'username': sender,
                'typing': False
            }, room=active_users[recipient])
    
    
    @socketio.on('message_read')
    def handle_message_read(data):
        """Handle message read receipt"""
        if 'username' not in session:
            return
        
        message_id = data.get('message_id')
        sender = data.get('sender')  # Original message sender
        reader = session['username']
        
        logger.info(f"Read receipt: {reader} read message {message_id} from {sender}")
        
        try:
            Message.mark_as_read(message_id)
            
            # Notify original sender
            if sender and sender in active_users:
                logger.info(f"Sending read status to {sender}")
                socketio.emit('message_status_update', {
                    'message_id': message_id,
                    'status': 'read'
                }, room=active_users[sender])
            else:
                logger.info(f"Sender {sender} not online, status update queued")
                
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
    
    
    @socketio.on('join_room')
    def handle_join_room(data):
        """Join a chat room (for group chats)"""
        if 'username' not in session:
            return
        
        room = data.get('room')
        if room:
            join_room(room)
            logger.info(f"User {session['username']} joined room {room}")
    
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        """Leave a chat room"""
        if 'username' not in session:
            return
        
        room = data.get('room')
        if room:
            leave_room(room)
            logger.info(f"User {session['username']} left room {room}")
    
    
    @socketio.on('add_reaction')
    def handle_add_reaction(data):
        """Handle adding reaction to a message"""
        if 'username' not in session:
            return
        
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        recipient = data.get('recipient')
        
        try:
            username = session['username']
            Message.add_reaction(message_id, username, emoji)
            
            # Notify both users
            reaction_data = {
                'message_id': message_id,
                'username': username,
                'emoji': emoji
            }
            
            # Notify recipient if online
            if recipient and recipient in active_users:
                socketio.emit('reaction_added', reaction_data, room=active_users[recipient])
            
            # Confirm to sender
            emit('reaction_added', reaction_data)
            
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            emit('error', {'message': 'Failed to add reaction'})
    
    
    @socketio.on('send_group_message')
    def handle_send_group_message(data):
        """
        Handle sending encrypted group message
        
        Data:
            {
                'chat_id': 'group_<group_id>',
                'group_id': '<group_id>',
                'ciphertext': '...',
                'nonce': '...',
                'type': 'text',
                'metadata': {...}
            }
        """
        if 'username' not in session:
            emit('error', {'message': 'Not authenticated'})
            return
        
        from app.models import Group
        
        sender = session['username']
        group_id = data.get('group_id')
        chat_id = data.get('chat_id')
        ciphertext = data.get('ciphertext')
        nonce = data.get('nonce')
        msg_type = data.get('type', 'text')
        metadata = data.get('metadata', {})
        
        # Validate data
        if not all([chat_id, group_id, ciphertext, nonce]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        try:
            # Verify user is member of group
            group = Group.find_by_id(group_id)
            if not group or sender not in group['members']:
                emit('error', {'message': 'Not authorized'})
                return
            
            # Store message in database
            message_id = Message.create(
                chat_id=chat_id,
                sender=sender,
                recipient=None,  # No single recipient for group
                ciphertext=ciphertext,
                nonce=nonce,
                ephemeral_pub=None,
                msg_type=msg_type,
                metadata=metadata,
                chat_type='group',
                group_id=group_id
            )
            
            # Prepare message for delivery
            message_data = {
                'message_id': message_id,
                'chat_id': chat_id,
                'group_id': group_id,
                'sender': sender,
                'ciphertext': ciphertext,
                'nonce': nonce,
                'type': msg_type,
                'metadata': metadata,
                'timestamp': data.get('timestamp'),
                'isGroup': True
            }
            
            # Send to all group members except sender
            for member in group['members']:
                if member != sender and member in active_users:
                    socketio.emit('receive_group_message', message_data,
                                room=active_users[member])
            
            # Send confirmation to sender
            emit('message_sent', {
                'message_id': message_id,
                'chat_id': chat_id,
                'status': 'sent',
                'timestamp': data.get('timestamp')
            })
            
            logger.info(f"Group message from {sender} in group {group_id}: {message_id}")
            
        except Exception as e:
            logger.error(f"Error sending group message: {e}")
            emit('error', {'message': 'Failed to send group message'})
    
    
    @socketio.on('group_created')
    def handle_group_created(data):
        """Notify members when a new group is created"""
        if 'username' not in session:
            return
        
        group_id = data.get('group_id')
        group_name = data.get('group_name')
        members = data.get('members', [])
        
        notification_data = {
            'group_id': group_id,
            'group_name': group_name,
            'creator': session['username']
        }
        
        # Notify all members except creator
        for member in members:
            if member != session['username'] and member in active_users:
                socketio.emit('group_notification', notification_data,
                            room=active_users[member])
        
        logger.info(f"Group {group_name} created by {session['username']}")
    
    
    @socketio.on('member_added')
    def handle_member_added(data):
        """Notify group members when a new member is added"""
        if 'username' not in session:
            return
        
        group_id = data.get('group_id')
        new_member = data.get('new_member')
        members = data.get('members', [])
        
        notification_data = {
            'group_id': group_id,
            'new_member': new_member,
            'added_by': session['username'],
            'members': members
        }
        
        # Notify all group members
        for member in members:
            if member in active_users:
                socketio.emit('group_member_added', notification_data,
                            room=active_users[member])
        
        logger.info(f"Member {new_member} added to group {group_id} by {session['username']}")
    
    
    @socketio.on('member_removed')
    def handle_member_removed(data):
        """Notify group members when a member is removed"""
        if 'username' not in session:
            return
        
        group_id = data.get('group_id')
        removed_member = data.get('removed_member')
        members = data.get('members', [])
        
        notification_data = {
            'group_id': group_id,
            'removed_member': removed_member,
            'removed_by': session['username'],
            'members': members,
            'key_rotated': True
        }
        
        # Notify remaining members (and the removed member)
        all_to_notify = members + [removed_member]
        for member in all_to_notify:
            if member in active_users:
                socketio.emit('group_member_removed', notification_data,
                            room=active_users[member])
        
        logger.info(f"Member {removed_member} removed from group {group_id} by {session['username']}")
    
    
    @socketio.on('member_left')
    def handle_member_left(data):
        """Notify group members when someone leaves the group"""
        if 'username' not in session:
            return
        
        group_id = data.get('group_id')
        left_member = data.get('left_member')
        members = data.get('members', [])
        
        notification_data = {
            'group_id': group_id,
            'left_member': left_member,
            'members': members
        }
        
        # Notify remaining members
        for member in members:
            if member in active_users:
                socketio.emit('group_member_left', notification_data,
                            room=active_users[member])
        
        logger.info(f"Member {left_member} left group {group_id}")
    
    
    @socketio.on('delete_message')
    def handle_delete_message(data):
        """Handle deleting a message for everyone"""
        if 'username' not in session:
            return
        
        from app.models import Group
        
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')
        username = session['username']
        
        try:
            # Get the message to verify ownership
            message = Message.find_by_id(message_id)
            if not message:
                emit('error', {'message': 'Message not found'})
                return
            
            # Only sender can delete their own message
            if message['sender'] != username:
                emit('error', {'message': 'Not authorized'})
                return
            
            # Delete the message (or mark as deleted)
            Message.delete_message(message_id)
            
            deletion_data = {
                'message_id': message_id,
                'chat_id': chat_id
            }
            
            # Notify all participants
            if chat_id.startswith('group_'):
                # Group message - notify all group members
                group_id = chat_id.replace('group_', '')
                group = Group.find_by_id(group_id)
                if group:
                    for member in group['members']:
                        if member in active_users:
                            socketio.emit('message_deleted', deletion_data,
                                        room=active_users[member])
            else:
                # Direct message - notify recipient
                recipient = message.get('recipient')
                if recipient and recipient in active_users:
                    socketio.emit('message_deleted', deletion_data,
                                room=active_users[recipient])
                
                # Confirm to sender
                emit('message_deleted', deletion_data)
            
            logger.info(f"Message {message_id} deleted by {username}")
            
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            emit('error', {'message': 'Failed to delete message'})
    
    
    @socketio.on('send_server_message')
    def handle_send_server_message(data):
        """Handle sending message to server-wide chat (public, no E2E encryption)"""
        if 'username' not in session:
            emit('error', {'message': 'Not authenticated'})
            return
        
        from app.models import ServerChat
        from app.routes.server_chat import invalidate_cache
        
        sender = session['username']
        message_text = data.get('message')
        
        if not message_text:
            emit('error', {'message': 'Missing message'})
            return
        
        try:
            # Store message in database (no encryption)
            message_doc = ServerChat.create(sender, message_text)
            
            # Invalidate message cache since we added a new message
            invalidate_cache()
            
            # Prepare message for broadcast (convert ObjectId to string)
            message_data = {
                '_id': str(message_doc['_id']),
                'sender': sender,
                'message': message_text,
                'timestamp': message_doc['timestamp'],
                'reactions': message_doc.get('reactions', {})
            }
            
            # Broadcast to all connected users
            socketio.emit('receive_server_message', message_data, broadcast=True)
            
            logger.info(f"Server message from {sender}: {message_doc['_id']}")
            
        except Exception as e:
            logger.error(f"Error sending server message: {e}")
            emit('error', {'message': 'Failed to send server message'})
    
    
    @socketio.on('server_message_reaction')
    def handle_server_message_reaction(data):
        """Handle adding reaction to server chat message"""
        if 'username' not in session:
            return
        
        from app.models import ServerChat
        
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        
        try:
            username = session['username']
            ServerChat.add_reaction(message_id, username, emoji)
            
            # Broadcast reaction to all users
            socketio.emit('server_reaction_added', {
                'message_id': message_id,
                'username': username,
                'emoji': emoji
            }, broadcast=True)
            
        except Exception as e:
            logger.error(f"Error adding server message reaction: {e}")
    
    
    @socketio.on('delete_server_message')
    def handle_delete_server_message(data):
        """Handle deleting server chat message"""
        if 'username' not in session:
            return
        
        from app.models import ServerChat
        
        message_id = data.get('message_id')
        username = session['username']
        
        try:
            # Note: You may want to add admin check here
            ServerChat.delete_message(message_id)
            
            # Broadcast deletion to all users
            socketio.emit('server_message_deleted', {
                'message_id': message_id
            }, broadcast=True)
            
            logger.info(f"Server message {message_id} deleted by {username}")
            
        except Exception as e:
            logger.error(f"Error deleting server message: {e}")
