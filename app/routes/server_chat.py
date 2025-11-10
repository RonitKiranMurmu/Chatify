"""
Routes for server-wide chat (public chat room)
"""
from flask import Blueprint, session, jsonify
from app.models import ServerChat
from app.utils.security import login_required
from datetime import datetime, timedelta

server_chat_bp = Blueprint('server_chat', __name__, url_prefix='/server-chat')

# Simple in-memory cache with timestamp
_message_cache = {
    'messages': [],
    'timestamp': None,
    'ttl': 30  # Cache for 30 seconds
}


def get_cached_messages():
    """Get messages from cache if valid, otherwise fetch from database"""
    now = datetime.utcnow()
    
    # Check if cache is valid
    if (_message_cache['timestamp'] and 
        (now - _message_cache['timestamp']).total_seconds() < _message_cache['ttl'] and
        _message_cache['messages']):
        return _message_cache['messages']
    
    # Cache miss or expired - fetch from database
    messages = ServerChat.get_recent_messages(limit=100)
    
    # Convert ObjectId to string
    for msg in messages:
        msg['_id'] = str(msg['_id'])
    
    # Reverse to get chronological order (oldest first)
    messages.reverse()
    
    # Update cache
    _message_cache['messages'] = messages
    _message_cache['timestamp'] = now
    
    return messages


def invalidate_cache():
    """Invalidate the message cache (call when new message is added)"""
    _message_cache['messages'] = []
    _message_cache['timestamp'] = None


@server_chat_bp.route('/messages', methods=['GET'])
@login_required
def get_server_messages():
    """Get recent server chat messages (with caching)"""
    try:
        messages = get_cached_messages()
        
        return jsonify({
            'success': True,
            'messages': messages
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
