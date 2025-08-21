workers = 3
bind = "0.0.0.0:$PORT"
timeout = 120
worker_class = "gevent"
loglevel = "info"

def post_fork(server, worker):
    from app import init_mongo
    init_mongo()  # Use existing MongoDB client