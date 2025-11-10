"""
Key management routes
"""
from flask import Blueprint, request, jsonify, session
from app.models import User
from app.utils.security import login_required

bp = Blueprint('keys', __name__, url_prefix='/keys')


@bp.route('/<username>', methods=['GET'])
@login_required
def get_user_keys(username):
    """
    Get user's public key bundle for key exchange
    
    Returns:
        {
            'identity_pub': '...',
            'signed_prekey_pub': '...',
            'signed_prekey_sig': '...',
            'one_time_prekey': {...} or null
        }
    """
    keys = User.get_public_keys(username)
    
    if not keys:
        return jsonify({'error': 'User not found'}), 404
    
    # Get one one-time prekey (if available)
    one_time_prekey = User.consume_one_time_prekey(username)
    
    return jsonify({
        'username': username,
        'identity_pub': keys['identity_pub'],
        'signed_prekey_pub': keys['signed_prekey_pub'],
        'signed_prekey_sig': keys['signed_prekey_sig'],
        'one_time_prekey': one_time_prekey
    }), 200


@bp.route('/refresh-prekeys', methods=['POST'])
@login_required
def refresh_prekeys():
    """
    Upload new one-time prekeys
    
    Body:
        {
            'one_time_prekeys': [
                {'id': 'opk1', 'key': '...', 'used': false},
                ...
            ]
        }
    """
    data = request.get_json()
    one_time_prekeys = data.get('one_time_prekeys', [])
    
    if not one_time_prekeys:
        return jsonify({'error': 'No prekeys provided'}), 400
    
    username = session['username']
    
    try:
        User.add_one_time_prekeys(username, one_time_prekeys)
        return jsonify({
            'success': True,
            'message': f'Added {len(one_time_prekeys)} prekeys'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/verify/<username>', methods=['GET'])
@login_required
def get_key_fingerprint(username):
    """
    Get user's identity key fingerprint for verification
    
    Returns:
        {
            'username': '...',
            'identity_pub': '...',
            'fingerprint': '...'
        }
    """
    keys = User.get_public_keys(username)
    
    if not keys:
        return jsonify({'error': 'User not found'}), 404
    
    # Calculate fingerprint (first 16 chars of identity key)
    identity_pub = keys['identity_pub']
    fingerprint = identity_pub[:16] if len(identity_pub) >= 16 else identity_pub
    
    return jsonify({
        'username': username,
        'identity_pub': identity_pub,
        'fingerprint': fingerprint
    }), 200
