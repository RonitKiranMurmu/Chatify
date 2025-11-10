"""
File upload/download routes
"""
from flask import Blueprint, request, jsonify, send_file, session, current_app
from werkzeug.utils import secure_filename
from app.utils.security import login_required, allowed_file, hash_file
import os
import uuid

bp = Blueprint('files', __name__, url_prefix='/files')


@bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """
    Upload encrypted file
    
    Form data:
        file: Binary file data (already encrypted on client)
        filename: Original filename
        file_hash: SHA-256 hash for integrity verification
        metadata: JSON metadata (optional)
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    original_filename = request.form.get('filename', file.filename)
    provided_hash = request.form.get('file_hash')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file extension
    if not allowed_file(original_filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > current_app.config['MAX_FILE_SIZE']:
        return jsonify({'error': 'File too large (max 16MB)'}), 400
    
    # Read file data
    file_data = file.read()
    
    # Verify file hash
    calculated_hash = hash_file(file_data)
    if provided_hash and provided_hash != calculated_hash:
        return jsonify({'error': 'File integrity check failed'}), 400
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    safe_filename = f"{file_id}.{file_extension}" if file_extension else file_id
    
    # Save file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, safe_filename)
    
    with open(file_path, 'wb') as f:
        f.write(file_data)
    
    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': original_filename,
        'size': file_size,
        'hash': calculated_hash
    }), 201


@bp.route('/download/<file_id>', methods=['GET'])
@login_required
def download_file(file_id):
    """
    Download encrypted file
    
    Returns:
        Binary file data (still encrypted)
    """
    # Find file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    # Search for file with any extension
    matching_files = [f for f in os.listdir(upload_folder) if f.startswith(file_id)]
    
    if not matching_files:
        return jsonify({'error': 'File not found'}), 404
    
    file_path = os.path.join(upload_folder, matching_files[0])
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)


@bp.route('/info/<file_id>', methods=['GET'])
@login_required
def get_file_info(file_id):
    """Get file information"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    
    # Search for file
    matching_files = [f for f in os.listdir(upload_folder) if f.startswith(file_id)]
    
    if not matching_files:
        return jsonify({'error': 'File not found'}), 404
    
    file_path = os.path.join(upload_folder, matching_files[0])
    file_size = os.path.getsize(file_path)
    
    return jsonify({
        'file_id': file_id,
        'size': file_size,
        'filename': matching_files[0]
    }), 200
