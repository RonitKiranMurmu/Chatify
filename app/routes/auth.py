"""
Authentication routes
"""
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, current_app
from app.models import User
from app.utils.security import hash_password, verify_password, validate_username, validate_password

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'GET':
        return render_template('register.html')
    
    # POST request - handle registration
    data = request.get_json() if request.is_json else request.form
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # Validate inputs
    is_valid, error = validate_username(username)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    is_valid, error = validate_password(password)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    # Check if username already exists
    if User.find_by_username(username):
        return jsonify({'error': 'Username already exists'}), 400
    
    # Get public keys from request
    identity_pub = data.get('identity_pub')
    signed_prekey_pub = data.get('signed_prekey_pub')
    signed_prekey_sig = data.get('signed_prekey_sig')
    one_time_prekeys = data.get('one_time_prekeys', [])
    
    if not all([identity_pub, signed_prekey_pub, signed_prekey_sig]):
        return jsonify({'error': 'Missing public keys'}), 400
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create user
    try:
        user_id = User.create(
            username=username,
            password_hash=password_hash,
            identity_pub=identity_pub,
            signed_prekey_pub=signed_prekey_pub,
            signed_prekey_sig=signed_prekey_sig,
            one_time_prekeys=one_time_prekeys
        )
        
        # Auto-login after registration
        session['user_id'] = user_id
        session['username'] = username
        session.permanent = True
        
        # Notify all connected users about new user
        from app import socketio
        socketio.emit('new_user_registered', {
            'username': username,
            'user_id': user_id
        })
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user_id': user_id,
            'username': username
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST request - handle login
    data = request.get_json() if request.is_json else request.form
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Find user
    user = User.find_by_username(username)
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Create session
    session['user_id'] = str(user['_id'])
    session['username'] = username
    session.permanent = data.get('remember_me', False)
    
    # Update online status
    User.update_online_status(username, True)
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user_id': str(user['_id']),
        'username': username
    }), 200


@bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """User logout"""
    username = session.get('username')
    
    if username:
        # Update online status
        User.update_online_status(username, False)
    
    # Clear session
    session.clear()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out'}), 200
    
    return redirect(url_for('index'))


@bp.route('/check-session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user_id': session['user_id'],
            'username': session['username']
        }), 200
    
    return jsonify({'logged_in': False}), 200
