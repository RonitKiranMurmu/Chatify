"""
Chatify - Secure Decentralized Chat Application
Main application entry point
"""
from app import create_app, socketio
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    host = app.config['HOST']
    port = app.config['PORT']
    debug = app.config['DEBUG']
    
    print(f"""
    ╔═══════════════════════════════════════════╗
    ║         Chatify - Secure Chat App         ║
    ║     End-to-End Encrypted Messaging        ║
    ╚═══════════════════════════════════════════╝
    
    🚀 Server starting...
    📍 URL: http://{host}:{port}
    🔧 Debug Mode: {debug}
    🗄️  Database: {app.config['MONGODB_URI'].split('@')[-1] if '@' in app.config['MONGODB_URI'] else 'Local MongoDB'}
    
    📝 Press Ctrl+C to stop the server
    """)
    
    # Run with Socket.IO
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
        log_output=True
    )
