workers = 3
bind = "0.0.0.0:$PORT"
timeout = 120  # Increased to handle blockchain mining
worker_class = "gevent"  # Use gevent for WebSocket support
loglevel = "info"

def post_fork(server, worker):
    from app import init_mongo  # Import init_mongo from app.py
    init_mongo()  # Initialize MongoDB after fork