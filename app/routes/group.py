"""
Group management routes
"""
from flask import Blueprint, request, jsonify, session
from app.models import Group, User
from bson import ObjectId

group_bp = Blueprint('group', __name__, url_prefix='/group')


@group_bp.route('/create', methods=['POST'])
def create_group():
    """Create a new group"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    group_name = data.get('group_name')
    members = data.get('members', [])
    group_key_encrypted = data.get('group_key_encrypted', {})
    
    if not group_name:
        return jsonify({'error': 'Group name is required'}), 400
    
    # Add admin to members if not already included
    admin = session['username']
    if admin not in members:
        members.append(admin)
    
    # Validate all members exist
    for member in members:
        if not User.find_by_username(member):
            return jsonify({'error': f'User {member} not found'}), 404
    
    # Create group
    group_id = Group.create(
        group_name=group_name,
        admin=admin,
        members=members,
        group_key_encrypted=group_key_encrypted
    )
    
    return jsonify({
        'success': True,
        'group_id': group_id,
        'message': 'Group created successfully'
    })


@group_bp.route('/<group_id>', methods=['GET'])
def get_group(group_id):
    """Get group details"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.find_by_id(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if user is a member
    if session['username'] not in group['members']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Convert ObjectId to string
    group['_id'] = str(group['_id'])
    
    # Only return the requesting user's encrypted group key
    username = session['username']
    user_encrypted_key = group['group_key_encrypted'].get(username)
    
    return jsonify({
        'group_id': group['_id'],
        'group_name': group['group_name'],
        'admin': group['admin'],
        'members': group['members'],
        'encrypted_group_key': user_encrypted_key,
        'created_at': group['created_at'].isoformat() + 'Z'
    })


@group_bp.route('/list', methods=['GET'])
def list_groups():
    """Get all groups user is member of"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    groups = Group.get_user_groups(session['username'])
    
    # Convert ObjectIds to strings
    for group in groups:
        group['_id'] = str(group['_id'])
        group['created_at'] = group['created_at'].isoformat() + 'Z'
        # Don't send encrypted keys in list view
        del group['group_key_encrypted']
    
    return jsonify({'groups': groups})


@group_bp.route('/<group_id>/add-member', methods=['POST'])
def add_member(group_id):
    """Add member to group (admin only)"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.find_by_id(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if requester is admin
    if group['admin'] != session['username']:
        return jsonify({'error': 'Only admin can add members'}), 403
    
    data = request.json
    new_member = data.get('username')
    encrypted_group_key = data.get('encrypted_group_key')
    
    if not new_member or not encrypted_group_key:
        return jsonify({'error': 'Username and encrypted group key required'}), 400
    
    # Check if user exists
    if not User.find_by_username(new_member):
        return jsonify({'error': 'User not found'}), 404
    
    # Check if already a member
    if new_member in group['members']:
        return jsonify({'error': 'User is already a member'}), 400
    
    # Add member
    Group.add_member(group_id, new_member, encrypted_group_key)
    
    return jsonify({
        'success': True,
        'message': f'{new_member} added to group'
    })


@group_bp.route('/<group_id>/remove-member', methods=['POST'])
def remove_member(group_id):
    """Remove member from group (admin only)"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.find_by_id(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if requester is admin
    if group['admin'] != session['username']:
        return jsonify({'error': 'Only admin can remove members'}), 403
    
    data = request.json
    member_to_remove = data.get('username')
    new_group_key_encrypted = data.get('new_group_key_encrypted', {})
    
    if not member_to_remove:
        return jsonify({'error': 'Username required'}), 400
    
    # Can't remove admin
    if member_to_remove == group['admin']:
        return jsonify({'error': 'Cannot remove admin'}), 400
    
    # Check if member exists in group
    if member_to_remove not in group['members']:
        return jsonify({'error': 'User is not a member'}), 404
    
    # Remove member
    Group.remove_member(group_id, member_to_remove)
    
    # Update group keys if new keys provided (key rotation)
    if new_group_key_encrypted:
        Group.update_group_keys(group_id, new_group_key_encrypted)
    
    return jsonify({
        'success': True,
        'message': f'{member_to_remove} removed from group'
    })


@group_bp.route('/<group_id>/leave', methods=['POST'])
def leave_group(group_id):
    """Leave a group"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.find_by_id(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    username = session['username']
    
    # Check if user is a member
    if username not in group['members']:
        return jsonify({'error': 'You are not a member of this group'}), 404
    
    # If admin is leaving, need special handling
    if username == group['admin']:
        # If there are other members, transfer admin to first member
        if len(group['members']) > 1:
            new_admin = [m for m in group['members'] if m != username][0]
            from app.utils.database import get_collection
            get_collection(Group.collection).update_one(
                {'_id': ObjectId(group_id)},
                {'$set': {'admin': new_admin}}
            )
        else:
            # Last member leaving, delete the group
            from app.utils.database import get_collection
            get_collection(Group.collection).delete_one({'_id': ObjectId(group_id)})
            return jsonify({
                'success': True,
                'message': 'Group deleted (you were the last member)'
            })
    
    # Remove user from group
    Group.remove_member(group_id, username)
    
    # Get updated group to return remaining members
    updated_group = Group.find_by_id(group_id)
    remaining_members = updated_group['members'] if updated_group else []
    
    return jsonify({
        'success': True,
        'message': 'You left the group',
        'remaining_members': remaining_members
    })


@group_bp.route('/<group_id>/history', methods=['GET'])
def get_group_history(group_id):
    """Get group message history"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    group = Group.find_by_id(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if user is a member
    if session['username'] not in group['members']:
        return jsonify({'error': 'Access denied'}), 403
    
    from app.models import Message
    
    # Get pagination parameters
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))
    
    # Get messages for this group
    messages = Message.get_chat_history(f'group_{group_id}', limit=limit, skip=skip)
    
    # Convert ObjectIds and timestamps to strings
    for msg in messages:
        msg['_id'] = str(msg['_id'])
        msg['timestamp'] = msg['timestamp'].isoformat() + 'Z'
    
    return jsonify({'messages': messages})
