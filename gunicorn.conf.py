workers = 3
bind = "0.0.0.0:8000"
timeout = 120  # Increased to handle blockchain mining
worker_class = "gevent"  # Use gevent for WebSocket support
loglevel = "info"
