import os
import json
import hashlib
import asyncio
import logging
import uuid
import time
import socket
from threading import Lock
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
import socketio as sio
from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("peerpulse")

# Load environment variables
load_dotenv()
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret!")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.environ.get("MONGO_DB", "peerpulse")
# Use raw 32-byte SHA256 digest to match CryptoJS
ENCRYPTION_KEY = hashlib.sha256("peerpulse-secret-2025".encode('utf-8')).digest()
logger.info(f"Server encryption key: {ENCRYPTION_KEY.hex()}")  # Log key for debugging

# Initialize MongoDB client at startup
mongo_client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,
    retryWrites=True,
    retryReads=True,
    connectTimeoutMS=10000,
    serverSelectionTimeoutMS=10000,
    tls=True,
    tlsAllowInvalidCertificates=False
)
db = mongo_client[MONGO_DB]
messages_col = db["messages"]
blocks_col = db["blocks"]
peers_col = db["peers"]

def init_mongo():
    global mongo_client, db, messages_col, blocks_col, peers_col
    try:
        # Ensure indexes
        messages_col.create_index([("msg_id", ASCENDING)], unique=True)
        messages_col.create_index([("timestamp", DESCENDING)])
        blocks_col.create_index([("index", ASCENDING)], unique=True)
        blocks_col.create_index([("previous_hash", ASCENDING)])
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
    return mongo_client

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

# Encryption/Decryption helpers
def encrypt_message(message):
    try:
        # Generate random IV
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(message.encode('utf-8'), AES.block_size))
        # Mimic CryptoJS OpenSSL format: Salted__ + salt (8 bytes) + IV (16 bytes) + ciphertext
        salt = os.urandom(8)  # Random 8-byte salt
        salted = b'Salted__' + salt + cipher.iv + ct_bytes
        return base64.b64encode(salted).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def decrypt_message(encrypted):
    try:
        # Decode base64 and parse OpenSSL format
        raw = base64.b64decode(encrypted)
        if not raw.startswith(b'Salted__'):
            raise ValueError("Invalid OpenSSL format: missing Salted__ header")
        # Extract salt (8 bytes), IV (16 bytes), and ciphertext
        salt = raw[8:16]
        iv = raw[16:32]
        ct = raw[32:]
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv=iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size).decode('utf-8')
        return pt
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None

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
    def _init_(self):
        try:
            self.chain = []
            self.pending_transactions = []
            self.load_chain_from_db()
            if not self.chain:
                self.create_genesis_block()
            logger.info("Blockchain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Blockchain: {e}")
            raise

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
        loop = asyncio.get_event_loop()
        base["hash"] = loop.run_until_complete(self.proof_of_work(base))
        self.chain.append(base)
        self._persist_block(base)
        logger.info("Genesis block created")

    async def proof_of_work(self, block: dict) -> str:
        start_time = time.time()
        block["nonce"] = 0
        computed_hash = await self.compute_hash(block)
        while not computed_hash.startswith("00"):
            block["nonce"] += 1
            computed_hash = await self.compute_hash(block)
            if time.time() - start_time > 5:
                logger.warning("Proof-of-work timeout, using partial hash")
                break
            await asyncio.sleep(0)
        return computed_hash

    def add_transaction(self, user_id, message, msg_type="text", filename="", ts=None):
        if isinstance(message, str):
            message = message.encode('utf-8', errors='ignore').decode('utf-8')
        if len(message) > 1000000:  # 1MB limit
            logger.error(f"Message too large from {user_id}")
            return False
        self.pending_transactions.append({
            "user_id": user_id,
            "message": message,
            "type": msg_type,
            "filename": filename,
            "timestamp": ts if ts is not None else time.time(),
        })
        return True

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
            logger.info(f"Loaded {len(self.chain)} blocks from database")
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
port = int(os.environ.get("PORT", 8000))
try:
    blockchain = Blockchain()
    logger.info("Blockchain instance created")
except Exception as e:
    logger.error(f"Failed to create Blockchain instance: {e}")
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

@app.route('/favicon.ico')
def favicon():
    logger.debug("Favicon requested, returning empty response")
    return Response(status=204)

# Socket.IO Events
@socketio.on('connect')
def handle_connect(auth=None):
    init_mongo()
    logger.debug("Client connected")
    emit("status", {"message": "Connected"})
    try:
        recent = list(messages_col.find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(20))
        for m in reversed(recent):
            m['timestamp'] = float(m['timestamp'])
            # Encrypt message for client
            if m['type'] == 'text':
                m['message'] = encrypt_message(m['message'])
            elif m['type'] == 'file':
                m['message'] = encrypt_message(m['message'])
            logger.debug(f"Sending recent message: {m}")
            emit("message", m)
    except Exception as e:
        logger.error(f"Failed to send recent messages: {e}")
        emit("status", {"message": f"Error fetching messages: {str(e)}"})
    emit("message", {
        "user_id": "System",
        "message": encrypt_message("Welcome to PeerPulse!"),
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
        "message": encrypt_message(f"{username} joined the chat"),
        "msg_id": str(uuid.uuid4()),
        "type": "text",
        "timestamp": time.time()
    }, broadcast=True)

@socketio.on("typing")
def handle_typing(data):
    logger.debug(f"Typing event from {data.get('user_id')}")
    emit("typing", data, broadcast=True, include_self=False)

@socketio.on("stop_typing")
def handle_stop_typing(data):
    logger.debug(f"Stop typing event from {data.get('user_id')}")
    emit("stop_typing", data, broadcast=True, include_self=False)

@socketio.on("message")
def handle_message(data):
    start_time = time.time()
    user_id = data.get("user_id", "Unknown")
    msg = data.get("message", "")
    msg_id = data.get("msg_id", str(uuid.uuid4()))
    msg_type = data.get("type", "text")
    filename = data.get("filename", "")
    ts = float(data.get("timestamp", time.time()))

    if msg_id in processed_messages:
        logger.debug(f"Duplicate message {msg_id} ignored")
        return
    processed_messages.add(msg_id)

    # Decrypt incoming message
    decrypted_msg = decrypt_message(msg)
    if decrypted_msg is None:
        logger.error(f"Decryption failed for message {msg_id} from {user_id}")
        emit("status", {"message": "Error decrypting message"})
        return

    logger.debug(f"Received {msg_type} from {user_id}, ID: {msg_id}, Decrypted: {decrypted_msg}")

    try:
        # Store decrypted message in MongoDB
        messages_col.insert_one({
            "user_id": user_id,
            "message": decrypted_msg,
            "msg_id": msg_id,
            "type": msg_type,
            "filename": filename,
            "timestamp": ts
        })
        logger.debug(f"Message {msg_id} inserted into MongoDB")
    except Exception as e:
        logger.error(f"Message insert failed for {msg_id}: {e}")
        emit("status", {"message": f"Error saving message: {str(e)}"})
        return

    if not blockchain.add_transaction(user_id, decrypted_msg, msg_type, filename, ts):
        logger.error(f"Failed to add transaction for {msg_id}: Message too large")
        emit("status", {"message": "Message too large"})
        return

    blockchain.async_mine_block()

    # Encrypt message for broadcast
    encrypted_msg = encrypt_message(decrypted_msg)
    if encrypted_msg is None:
        logger.error(f"Encryption failed for broadcast of {msg_id}")
        emit("status", {"message": "Error encrypting message for broadcast"})
        return

    msg_data = {
        "user_id": user_id,
        "message": encrypted_msg,
        "msg_id": msg_id,
        "type": msg_type,
        "filename": filename,
        "timestamp": ts
    }
    logger.debug(f"Broadcasting message: {msg_data}")
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
                    decrypted_tx = decrypt_message(tx["message"])
                    if decrypted_tx is None:
                        logger.error(f"Decryption failed for blockchain transaction: {tx}")
                        continue
                    tx["message"] = decrypted_tx
        loop = asyncio.get_event_loop()
        if loop.run_until_complete(blockchain.replace_chain(received_chain)):
            logger.info("Blockchain updated from peer")
            for block in blockchain.chain:
                for tx in block.get("transactions", []):
                    mid = str(uuid.uuid4())
                    processed_messages.add(mid)
                    encrypted_tx = encrypt_message(tx["message"])
                    if encrypted_tx is None:
                        logger.error(f"Encryption failed for blockchain transaction: {tx}")
                        continue
                    emit("message", {
                        "user_id": tx.get("user_id", "Unknown"),
                        "message": encrypted_tx,
                        "msg_id": mid,
                        "type": tx.get("type", "text"),
                        "filename": tx.get("filename", ""),
                        "timestamp": float(tx.get("timestamp", time.time()))
                    })
    except Exception as e:
        logger.error(f"Failed to decode received chain: {e}")
        emit("status", {"message": f"Error syncing blockchain: {str(e)}"})

@socketio.on("request_blockchain")
def handle_request_blockchain(data=None):
    try:
        if not hasattr(blockchain, 'chain'):
            logger.error("Blockchain object missing chain attribute")
            emit("status", {"message": "Error: Blockchain not properly initialized"})
            return
        offset = data.get("offset", 0) if data else 0
        limit = data.get("limit", 20) if data else 20
        chain_copy = blockchain.chain.copy()
        transactions = []
        for block in chain_copy:
            for tx in block.get("transactions", []):
                if isinstance(tx.get("message"), str):
                    encrypted_tx = encrypt_message(tx["message"])
                    if encrypted_tx is None:
                        logger.error(f"Encryption failed for blockchain transaction: {tx}")
                        continue
                    tx["message"] = encrypted_tx
                transactions.append(tx)
        transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        for tx in transactions[offset:offset + limit]:
            emit("message", {
                "user_id": tx.get("user_id", "Unknown"),
                "message": tx.get("message", ""),
                "msg_id": str(uuid.uuid4()),
                "type": tx.get("type", "text"),
                "filename": tx.get("filename", ""),
                "timestamp": float(tx.get("timestamp", time.time()))
            })
        logger.info(f"Sent blockchain transactions (offset: {offset}, limit: {limit})")
    except Exception as e:
        logger.error(f"Failed to send blockchain: {e}")
        emit("status", {"message": f"Error fetching blockchain: {str(e)}"})

# Main
if __name__ == "_main_":
    port = int(os.environ.get("PORT", 8000))
    peer_ports = load_peers() or []
    local_ip = get_local_ip()
    logger.info(f"Starting server on http://0.0.0.0:{port} (accessible at http://{local_ip}:{port})")
    if peer_ports:
        connect_to_peers(peer_ports, host=local_ip)
    socketio.run(app, host="0.0.0.0", port=port, debug=True, use_reloader=False)