"""
Chatify Application Factory
"""
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from config import config
import os

# Initialize SocketIO
socketio = SocketIO()

def create_app(config_name=None):
    """
    Create and configure the Flask application
    
    Args:
        config_name: Configuration to use (development, production, testing)
    
    Returns:
        Flask app instance
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Get the parent directory (project root)
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(__name__, 
                template_folder=os.path.join(root_path, 'templates'),
                static_folder=os.path.join(root_path, 'static'))
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    CORS(app, origins=app.config['CORS_ORIGINS'])
    socketio.init_app(
        app,
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
        async_mode=app.config['SOCKETIO_ASYNC_MODE']
    )
    
    # Initialize database
    from app.utils.database import init_db
    init_db(app.config['MONGODB_URI'])
    
    # Register blueprints
    from app.routes import auth, chat, keys, files
    from app.routes.group import group_bp
    from app.routes.file import file_bp
    from app.routes.server_chat import server_chat_bp
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(keys.bp)
    app.register_blueprint(files.bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(server_chat_bp)
    
    # Register Socket.IO events
    from app import socket_events
    socket_events.register_events(socketio)
    
    # Home route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'chatify'}, 200
    
    return app
