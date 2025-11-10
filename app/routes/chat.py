"""
Chat routes
"""
from flask import Blueprint, request, jsonify, render_template, session
from app.models import Message, User
from app.utils.security import login_required

bp = Blueprint('chat', __name__, url_prefix='/chat')


@bp.route('/', methods=['GET'])
@login_required
def chat_page():
    """Render main chat interface"""
    return render_template('chat.html', username=session['username'])


@bp.route('/history/<chat_id>', methods=['GET'])
@login_required
def get_history(chat_id):
    """Get chat history"""
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))
    
    messages = Message.get_chat_history(chat_id, limit, skip)
    
    # Convert ObjectId to string and format timestamp as UTC ISO string
    for msg in messages:
        msg['_id'] = str(msg['_id'])
        # Add 'Z' suffix to indicate UTC timezone
        msg['timestamp'] = msg['timestamp'].isoformat() + 'Z'
    
    return jsonify({'messages': messages}), 200


@bp.route('/contacts', methods=['GET'])
@login_required
def get_contacts():
    """Get list of all contacts (alias for /users)"""
    users = User.get_all_users(exclude_username=session['username'])
    
    # Format users as contacts
    contacts = []
    for user in users:
        contacts.append({
            'username': user['username'],
            'is_online': user.get('is_online', False)
        })
    
    return jsonify({'contacts': contacts}), 200


@bp.route('/users', methods=['GET'])
@login_required
def get_users():
    """Get list of all users"""
    from app.socket_events import active_users
    
    users = User.get_all_users(exclude_username=session['username'])
    
    # Convert ObjectId to string and format response
    formatted_users = []
    for user in users:
        # Check if user is actually connected via Socket.IO (more reliable than DB status)
        is_actually_online = user['username'] in active_users
        
        formatted_users.append({
            'id': str(user['_id']),
            'username': user['username'],
            'is_online': is_actually_online,
            'last_seen': user.get('last_seen').isoformat() if user.get('last_seen') else None
        })
    
    return jsonify({'users': formatted_users}), 200


@bp.route('/message/read/<message_id>', methods=['POST'])
@login_required
def mark_read(message_id):
    """Mark message as read"""
    try:
        Message.mark_as_read(message_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/message/delivered/<message_id>', methods=['POST'])
@login_required
def mark_delivered(message_id):
    """Mark message as delivered"""
    try:
        Message.mark_as_delivered(message_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/message/react/<message_id>', methods=['POST'])
@login_required
def add_reaction(message_id):
    """Add reaction to message"""
    data = request.get_json()
    emoji = data.get('emoji')
    
    if not emoji:
        return jsonify({'error': 'Emoji required'}), 400
    
    try:
        Message.add_reaction(message_id, session['username'], emoji)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/message/delete/<message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """Delete a message"""
    try:
        Message.delete_message(message_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/prekey-bundle/<username>', methods=['GET'])
@login_required
def get_prekey_bundle(username):
    """Get user's public prekey bundle for key exchange"""
    try:
        # Get user's public keys
        user_keys = User.get_public_keys(username)
        
        if not user_keys:
            return jsonify({'error': 'User not found'}), 404
        
        # Get one unused one-time prekey (if available)
        one_time_prekey = User.consume_one_time_prekey(username)
        
        # Prepare prekey bundle
        bundle = {
            'username': username,
            'identity_pub': user_keys.get('identity_pub'),
            'signed_prekey_pub': user_keys.get('signed_prekey_pub'),
            'signed_prekey_sig': user_keys.get('signed_prekey_sig'),
            'one_time_prekey': one_time_prekey['publicKey'] if one_time_prekey else None
        }
        
        return jsonify(bundle), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch prekey bundle: {str(e)}'}), 500


@bp.route('/upload-prekeys', methods=['POST'])
@login_required
def upload_prekeys():
    """Upload new one-time prekeys (for key rotation)"""
    data = request.get_json()
    
    new_prekeys = data.get('one_time_prekeys', [])
    
    if not new_prekeys:
        return jsonify({'error': 'No prekeys provided'}), 400
    
    try:
        User.add_one_time_prekeys(session['username'], new_prekeys)
        return jsonify({'success': True, 'count': len(new_prekeys)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/unread-counts', methods=['GET'])
@login_required
def get_unread_counts():
    """Get unread message counts for all chats"""
    try:
        current_user = session['username']
        unread_counts = Message.get_unread_counts(current_user)
        return jsonify({'unread_counts': unread_counts}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
