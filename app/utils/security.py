"""
Security utility functions
"""
import bcrypt
import secrets
import hashlib
from functools import wraps
from flask import session, redirect, url_for, request, jsonify


def hash_password(password):
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password as string
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    """
    Verify a password against a hash
    
    Args:
        password: Plain text password
        hashed: Hashed password
    
    Returns:
        Boolean indicating if password matches
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def generate_token(length=32):
    """
    Generate a secure random token
    
    Args:
        length: Length of token in bytes
    
    Returns:
        Hex token string
    """
    return secrets.token_hex(length)


def hash_file(file_data):
    """
    Generate SHA-256 hash of file data
    
    Args:
        file_data: Binary file data
    
    Returns:
        Hex digest of file hash
    """
    return hashlib.sha256(file_data).hexdigest()


def login_required(f):
    """
    Decorator to require login for routes
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected():
            return "This is protected"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def validate_username(username):
    """
    Validate username format
    
    Args:
        username: Username to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 30:
        return False, "Username must be less than 30 characters"
    
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    return True, None


def validate_password(password):
    """
    Validate password strength
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    # Check for at least one digit and one letter
    has_digit = any(c.isdigit() for c in password)
    has_letter = any(c.isalpha() for c in password)
    
    if not (has_digit and has_letter):
        return False, "Password must contain both letters and numbers"
    
    return True, None


def allowed_file(filename, allowed_extensions):
    """
    Check if file extension is allowed
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions
    
    Returns:
        Boolean indicating if file is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions
