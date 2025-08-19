import os
import json
import hashlib
import asyncio
import logging
import uuid
import time
import socket
from threading import Lock, Thread
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
import socketio as sio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("peerpulse")

# Load environment variables
load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret!")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.environ.get("MONGO_DB", "peerpulse")

# Initialize MongoDB client after fork
mongo_client = None
db = None
messages_col = None
blocks_col = None
peers_col = None

def init_mongo():
    global mongo_client, db, messages_col, blocks_col, peers_col
    try:
        mongo_client = MongoClient(MONGO_URI, maxPoolSize=50, retryWrites=True, retryReads=True, connectTimeoutMS=10000, serverSelectionTimeoutMS=10000)
        db = mongo_client[MONGO_DB]
        messages_col = db["messages"]
        blocks_col = db["blocks"]
        peers_col = db["peers"]
        messages_col.create_index([("msg_id", ASCENDING)], unique=True)
        messages_col.create_index([("timestamp", DESCENDING)])
        blocks_col.create_index([("index", ASCENDING)], unique=True)
        blocks_col.create_index([("previous_hash", ASCENDING)])
        logger.info("MongoDB connection established")
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

# Initialize SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=120,
    ping_interval=40,
    transports=['websocket'],
    async_mode='gevent',
    logger=True,
    engineio_logger=True
)

# Thread lock for mining
mine_lock = Lock()

# Helpers
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def load_peers():
    try:
        with open("peers.json", "r") as f:
            peers = json.load(f)
            if os.environ.get("RENDER") == "true":
                peers = [p.replace("http://localhost", "https://chatify-fcw1.onrender.com/") for p in peers]
            return peers
    except FileNotFoundError:
        logger.warning("peers.json not found, using command-line peer ports")
        return []

# Blockchain
class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.load_chain_from_db()
        if not self.chain:
            self.create_genesis_block()

    @staticmethod
    async def compute_hash(block: dict) -> str:
        block_copy = {k: v for k, v in block.items() if k != "hash"}
        block_string = json.dumps(block_copy, sort_keys=True, default=str)
        return hashlib.sha256(block_string.encode('utf-8', errors='ignore')).hexdigest()

    def create_genesis_block(self):
        base = {
            "index": 0,
            "timestamp": time.time(),
            "transactions": [],
            "previous_hash": "0",
            "nonce": 0,
        }
        base["hash"] = asyncio.get_event_loop().run_until_complete(self.proof_of_work(base))
        self.chain.append(base)
        self._persist_block(base)
        logger.info("Genesis block created")

    async def proof_of_work(self, block: dict) -> str:
        start_time = time.time()
        block["nonce"] = 0
        computed_hash = await self.compute_hash(block)
        while not computed_hash.startswith("00"):  # Reduced difficulty
            block["nonce"] += 1
            computed_hash = await self.compute_hash(block)
            if time.time() - start_time > 5:
                logger.warning("Proof-of-work timeout, using partial hash")
                break
            await asyncio.sleep(0)  # Yield control
        return computed_hash

    def add_transaction(self, user_id, message, msg_type="text", filename="", ts=None):
        if isinstance(message, str):
            message = message.encode('utf-8', errors='ignore').decode('utf-8')
        self.pending_transactions.append({
            "user_id": user_id,
            "message": message,
            "type": msg_type,
            "filename": filename,
            "timestamp": ts if ts is not None else time.time(),
        })

    async def mine_block(self):
        if not self.pending_transactions:
            return None
        with mine_lock:
            if not self.pending_transactions:
                return None
            block = {
                "index": len(self.chain),
                "timestamp": time.time(),
                "transactions": self.pending_transactions.copy(),
                "previous_hash": self.chain[-1]["hash"] if self.chain else "0",
                "nonce": 0,
            }
            block["hash"] = await self.proof_of_work(block)
            self.chain.append(block)
            self.pending_transactions = []
            self._persist_block(block)
            logger.debug(f"Mined block: {block['index']}")
            return block

    def async_mine_block(self):
        asyncio.run_coroutine_threadsafe(self.mine_block(), asyncio.get_event_loop())

    def _persist_block(self, block: dict):
        try:
            blocks_col.insert_one(block)
        except Exception as e:
            logger.error(f"Failed to persist block {block.get('index')}: {e}")

    def load_chain_from_db(self):
        try:
            self.chain = list(blocks_col.find({}, {"_id": 0}).sort("index", ASCENDING))
        except Exception as e:
            logger.error(f"Failed to load chain from DB: {e}")
            self.chain = []

    async def is_valid_chain(self, chain: list) -> bool:
        if not chain:
            return False
        g = chain[0]
        if g.get("previous_hash") != "0":
            return False
        if not (await self.compute_hash(g)).startswith("00"):
            return False
        if g.get("hash") != await self.compute_hash(g):
            return False
        for i in range(1, len(chain)):
            current = chain[i]
            prev = chain[i - 1]
            if current.get("previous_hash") != prev.get("hash"):
                return False
            if not (await self.compute_hash(current)).startswith("00"):
                return False
            if current.get("hash") != await self.compute_hash(current):
                return False
        return True

    async def replace_chain(self, new_chain: list) -> bool:
        if len(new_chain) <= len(self.chain):
            return False
        if not await self.is_valid_chain(new_chain):
            return False
        self.chain = new_chain
        try:
            blocks_col.delete_many({})
            if new_chain:
                blocks_col.insert_many(new_chain)
            logger.info("Blockchain replaced with longer valid chain from peer")
            return True
        except Exception as e:
            logger.error(f"Failed to replace chain in DB: {e}")
            return False

# Globals & Peer Clients
port = int(os.environ.get("PORT", 5000))
blockchain = Blockchain()
peers = []
peer_clients = []
processed_messages = set()

def connect_to_peers(peer_ports, host="localhost"):
    for p in peer_ports:
        peer_url = f"http://{host}:{p}" if os.environ.get("RENDER") != "true" else "https://chatify-fcw1.onrender.com/"
        if peer_url in peers:
            continue
        peers.append(peer_url)
        client = sio.Client()
        try:
            client.connect(peer_url, transports=['websocket'])
            peer_clients.append(client)
            logger.debug(f"Connected to peer: {peer_url}")
            client.emit("sync_blockchain", json.dumps(blockchain.chain, default=str))
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer_url}: {e}")

# Routes
@app.route("/")
def index():
    logger.debug("Serving index.html")
    return render_template("index.html")

# Socket.IO Events
@socketio.on("connect")
def handle_connect():
    logger.debug("Client connected")
    init_mongo()  # Initialize MongoDB after fork
    emit("status", {"message": "Connected"})
    try:
        recent = list(messages_col.find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(20))
        for m in reversed(recent):
            m['timestamp'] = float(m['timestamp'])
            emit("message", m)
    except Exception as e:
        logger.error(f"Failed to send recent messages: {e}")
    emit("message", {
        "user_id": "System",
        "message": "Welcome to PeerPulse!",
        "msg_id": str(uuid.uuid4()),
        "type": "text",
        "timestamp": time.time()
    }, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    logger.debug("Client disconnected")

@socketio.on("join")
def handle_join(username):
    logger.debug(f"User joined: {username}")
    emit("message", {
        "user_id": "System",
        "message": f"{username} joined the chat",
        "msg_id": str(uuid.uuid4()),
        "type": "text",
        "timestamp": time.time()
    }, broadcast=True)

@socketio.on("message")
def handle_message(data):
    start_time = time.time()
    user_id = data.get("user_id", "Unknown")
    msg = data.get("message", "")
    if isinstance(msg, str):
        msg = msg.encode('utf-8', errors='ignore').decode('utf-8')
    msg_id = data.get("msg_id", str(uuid.uuid4()))
    msg_type = data.get("type", "text")
    filename = data.get("filename", "")
    ts = float(data.get("timestamp", time.time()))

    if msg_id in processed_messages:
        logger.debug(f"Duplicate message {msg_id} ignored")
        return
    processed_messages.add(msg_id)

    logger.debug(f"Received {msg_type} from {user_id}, ID: {msg_id}")

    try:
        messages_col.insert_one({
            "user_id": user_id,
            "message": msg,
            "msg_id": msg_id,
            "type": msg_type,
            "filename": filename,
            "timestamp": ts
        })
    except Exception as e:
        logger.error(f"Message insert failed for {msg_id}: {e}")
        return

    blockchain.add_transaction(user_id, msg, msg_type, filename, ts)
    blockchain.async_mine_block()

    msg_data = {
        "user_id": user_id,
        "message": msg,
        "msg_id": msg_id,
        "type": msg_type,
        "filename": filename,
        "timestamp": ts
    }
    emit("message", msg_data, broadcast=True)

    for client in peer_clients:
        try:
            client.emit("message", msg_data)
            client.emit("sync_blockchain", json.dumps(blockchain.chain, default=str))
            logger.debug("Forwarded message and blockchain to peer")
        except Exception as e:
            logger.error(f"Failed to forward to peer: {e}")

    latency = (time.time() - start_time) * 1000
    logger.info(f"Message processing latency: {latency:.2f} ms")

@socketio.on("sync_blockchain")
def handle_sync_blockchain(data):
    try:
        received_chain = json.loads(data)
        for block in received_chain:
            for tx in block.get("transactions", []):
                if isinstance(tx.get("message"), str):
                    tx["message"] = tx["message"].encode('utf-8', errors='ignore').decode('utf-8')
        loop = asyncio.get_event_loop()
        if loop.run_until_complete(blockchain.replace_chain(received_chain)):
            logger.info("Blockchain updated from peer")
            for block in blockchain.chain:
                for tx in block.get("transactions", []):
                    mid = str(uuid.uuid4())
                    processed_messages.add(mid)
                    emit("message", {
                        "user_id": tx.get("user_id", "Unknown"),
                        "message": tx.get("message", ""),
                        "msg_id": mid,
                        "type": tx.get("type", "text"),
                        "filename": tx.get("filename", ""),
                        "timestamp": float(tx.get("timestamp", time.time()))
                    })
    except Exception as e:
        logger.error(f"Failed to decode received chain: {e}")

@socketio.on("request_blockchain")
def handle_request_blockchain():
    try:
        chain_copy = blockchain.chain.copy()
        for block in chain_copy:
            for tx in block.get("transactions", []):
                if isinstance(tx.get("message"), str):
                    tx["message"] = tx["message"].encode('utf-8', errors='ignore').decode('utf-8')
        emit("sync_blockchain", json.dumps(chain_copy, default=str))
        logger.info("Sent blockchain to client")
    except Exception as e:
        logger.error(f"Failed to send blockchain: {e}")

# Main
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    peer_ports = load_peers() or []
    local_ip = get_local_ip()
    logger.info(f"Starting server on http://0.0.0.0:{port} (accessible at http://{local_ip}:{port})")
    if peer_ports:
        connect_to_peers(peer_ports, host=local_ip)
    socketio.run(app, host="0.0.0.0", port=port, debug=True, use_reloader=False)