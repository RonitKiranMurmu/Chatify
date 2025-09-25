import os

# Render provides PORT as environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"

# Use single worker for SocketIO compatibility
workers = 1
worker_class = "gevent"
worker_connections = 1000

# Timeout settings
timeout = 120
keepalive = 5

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Optimize for production
preload_app = True
max_requests = 1000
max_requests_jitter = 100

def post_fork(server, worker):
    """Initialize after forking worker"""
    try:
        from app import init_mongo
        init_mongo()
        server.log.info("MongoDB initialized in worker")
    except Exception as e:
        server.log.error(f"Failed to initialize MongoDB in worker: {e}")

def when_ready(server):
    """Called when server is ready"""
    server.log.info("Chatify server is ready for connections")