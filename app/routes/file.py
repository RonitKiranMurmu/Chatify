"""
File upload/download routes
Handles encrypted file storage and retrieval using MongoDB GridFS
"""
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from bson import ObjectId
import gridfs
import io
import hashlib
from app.utils.database import get_db

file_bp = Blueprint('file', __name__, url_prefix='/file')

# Initialize GridFS
db = get_db()
fs = gridfs.GridFS(db)

# File size limit: 16MB
MAX_FILE_SIZE = 16 * 1024 * 1024

# Allowed file extensions (for security)
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv',
    'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac',
    'zip', 'rar', '7z', 'tar', 'gz'
}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@file_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload encrypted file to GridFS
    
    Expected form data:
        - file: The encrypted file blob
        - filename: Original filename
        - file_type: MIME type
        - file_hash: SHA-256 hash for integrity
        - chat_id: Associated chat ID
        - recipient: Recipient username (for private chat) or group_id (for group)
    """
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get metadata
    original_filename = request.form.get('filename', file.filename)
    file_type = request.form.get('file_type', 'application/octet-stream')
    file_hash = request.form.get('file_hash')
    chat_id = request.form.get('chat_id')
    recipient = request.form.get('recipient')
    
    # Validate filename
    if not allowed_file(original_filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Read file data
    file_data = file.read()
    
    # Check file size
    if len(file_data) > MAX_FILE_SIZE:
        return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024)}MB'}), 400
    
    # Verify hash if provided
    if file_hash:
        calculated_hash = hashlib.sha256(file_data).hexdigest()
        if calculated_hash != file_hash:
            return jsonify({'error': 'File integrity check failed'}), 400
    
    # Store file in GridFS
    filename = secure_filename(original_filename)
    file_id = fs.put(
        file_data,
        filename=filename,
        content_type=file_type,
        sender=session['username'],
        chat_id=chat_id,
        recipient=recipient,
        file_hash=file_hash,
        original_size=len(file_data)
    )
    
    return jsonify({
        'success': True,
        'file_id': str(file_id),
        'filename': filename,
        'size': len(file_data)
    })


@file_bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download encrypted file from GridFS"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get file from GridFS
        file_obj = fs.get(ObjectId(file_id))
        
        # Check authorization (user must be sender or recipient)
        username = session['username']
        if file_obj.sender != username and file_obj.recipient != username:
            # For group files, check if user is in the group
            if not file_obj.chat_id.startswith('group_'):
                return jsonify({'error': 'Access denied'}), 403
        
        # Read file data
        file_data = file_obj.read()
        
        # Create response with file data
        return send_file(
            io.BytesIO(file_data),
            download_name=file_obj.filename,
            mimetype=file_obj.content_type
        )
        
    except gridfs.errors.NoFile:
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@file_bp.route('/info/<file_id>', methods=['GET'])
def get_file_info(file_id):
    """Get file metadata without downloading"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        file_obj = fs.get(ObjectId(file_id))
        
        return jsonify({
            'file_id': str(file_obj._id),
            'filename': file_obj.filename,
            'content_type': file_obj.content_type,
            'size': file_obj.original_size,
            'sender': file_obj.sender,
            'upload_date': file_obj.upload_date.isoformat() + 'Z'
        })
        
    except gridfs.errors.NoFile:
        return jsonify({'error': 'File not found'}), 404
