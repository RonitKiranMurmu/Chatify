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
log_level = logging.INFO if os.environ.get("RENDER") == "true" else logging.DEBUG
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("peerpulse")

# Load environment variables
load_dotenv()
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    logger.error("SECRET_KEY environment variable not set!")
    raise ValueError("SECRET_KEY must be set in environment variables")
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    logger.error("MONGO_URI environment variable not set!")
    raise ValueError("MONGO_URI must be set in environment variables")
MONGO_DB = os.environ.get("MONGO_DB", "peerpulse")
# Use environment-based encryption key for security
ENCRYPTION_SECRET = os.environ.get("ENCRYPTION_KEY", os.environ.get("ENCRYPTION_SECRET", "peerpulse-secret-2025"))
ENCRYPTION_KEY = hashlib.sha256(ENCRYPTION_SECRET.encode('utf-8')).digest()
ENCRYPTION_KEY_HEX = ENCRYPTION_KEY.hex()
logger.info("Secure encryption system initialized for P2P decentralized chat")

# Initialize MongoDB client at startup
is_atlas = MONGO_URI.startswith("mongodb+srv://") or "atlas" in MONGO_URI.lower()

def create_mongo_client():
    """Create MongoDB client with retry logic"""
    if is_atlas:
        return MongoClient(
            MONGO_URI,
            maxPoolSize=5,  # Further reduced for stability
            retryWrites=True,
            retryReads=True,
            connectTimeoutMS=60000,  # Much longer timeout
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            maxIdleTimeMS=120000,
            heartbeatFrequencyMS=30000,
            tls=True,
            tlsAllowInvalidCertificates=False,
            # Force TLS version
            tlsInsecure=False
        )
    else:
        return MongoClient(
            MONGO_URI,
            maxPoolSize=5,
            retryWrites=True,
            retryReads=True,
            connectTimeoutMS=60000,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            maxIdleTimeMS=120000
        )

# Initialize with retry
mongo_client = None
for attempt in range(3):
    try:
        mongo_client = create_mongo_client()
        mongo_client.admin.command('ping')
        logger.info(f"MongoDB connected successfully on attempt {attempt + 1}")
        break
    except Exception as e:
        logger.error(f"MongoDB connection attempt {attempt + 1} failed: {e}")
        if attempt == 2:
            logger.error("Failed to connect to MongoDB after 3 attempts")
            raise
        time.sleep(2)
db = mongo_client[MONGO_DB]
messages_col = db["messages"]
blocks_col = db["blocks"]

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Mining lock for thread safety
mine_lock = Lock()

def init_mongo():
    """Initialize MongoDB connection and verify it's working"""
    try:
        # Test the connection
        mongo_client.admin.command('ping')
        logger.info("MongoDB connection verified")
        return True
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"MongoDB initialization error: {e}")
        return False
peers_col = db["peers"]

def safe_mongo_operation(operation_func, *args, **kwargs):
    """Execute MongoDB operation with automatic reconnection"""
    global mongo_client, db, messages_col, blocks_col, peers_col
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            if "SSL" in str(e) or "socket" in str(e).lower() or attempt < max_retries - 1:
                logger.warning(f"MongoDB operation failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    # Recreate connection
                    try:
                        mongo_client = create_mongo_client()
                        db = mongo_client[MONGO_DB]
                        messages_col = db["messages"]
                        blocks_col = db["blocks"]
                        peers_col = db["peers"]
                        time.sleep(1)
                        logger.info("MongoDB connection recreated")
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect: {reconnect_error}")
                        time.sleep(2)
            else:
                raise e
    return None

def init_mongo():
    global mongo_client, db, messages_col, blocks_col, peers_col
    try:
        # Test connection first
        mongo_client.admin.command('ping')
        
        # Check for duplicate blocks and clean up if necessary
        def cleanup_duplicates():
            duplicates = list(blocks_col.aggregate([
                {"$group": {"_id": "$index", "count": {"$sum": 1}, "docs": {"$push": "$_id"}}},
                {"$match": {"count": {"$gt": 1}}}
            ]))
            
            for dup in duplicates:
                # Keep the first document, remove the rest
                docs_to_remove = dup["docs"][1:]
                if docs_to_remove:
                    blocks_col.delete_many({"_id": {"$in": docs_to_remove}})
                    logger.info(f"Removed {len(docs_to_remove)} duplicate blocks with index {dup['_id']}")
        
        safe_mongo_operation(cleanup_duplicates)
        
        # Ensure indexes (handle existing indexes gracefully)
        try:
            messages_col.create_index([("msg_id", ASCENDING)], unique=True)
        except Exception as e:
            if "duplicate key" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("Messages index already exists")
            else:
                logger.warning(f"Messages index creation issue: {e}")
        
        try:
            messages_col.create_index([("timestamp", DESCENDING)])
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Messages timestamp index already exists")
            else:
                logger.warning(f"Messages timestamp index issue: {e}")
        
        try:
            blocks_col.create_index([("index", ASCENDING)], unique=True)
        except Exception as e:
            if "duplicate key" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("Blocks index already exists")
            else:
                logger.warning(f"Blocks index creation issue: {e}")
        
        try:
            blocks_col.create_index([("previous_hash", ASCENDING)])
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Blocks previous_hash index already exists")
            else:
                logger.warning(f"Blocks previous_hash index issue: {e}")
        
        logger.info("MongoDB connection established and indexes verified")
    except Exception as e:
        logger.error(f"MongoDB initialization error: {e}")
    return mongo_client

# Initialize SocketIO
is_production = os.environ.get("RENDER") == "true"
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=120,
    ping_interval=40,
    transports=['websocket'],
    async_mode='gevent',
    logger=not is_production,  # Disable verbose logging in production
    engineio_logger=not is_production
)

# Thread lock for mining
mine_lock = Lock()

# Encryption/Decryption helpers
def encrypt_message(message):
    try:
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(message.encode('utf-8'), AES.block_size))
        return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def decrypt_message(encrypted):
    try:
        raw = base64.b64decode(encrypted)
        iv = raw[0:16]
        ct = raw[16:]
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
                render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
                peers = [p.replace("http://localhost", render_url) for p in peers]
            return peers
    except FileNotFoundError:
        logger.warning("peers.json not found, using command-line peer ports")
        return []

# Blockchain
class Blockchain:
    def __init__(self):
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
        asyncio.run(self.mine_block())  # Runs the async method synchronously

    def _persist_block(self, block: dict):
        try:
            blocks_col.insert_one(block)
        except Exception as e:
            logger.error(f"Failed to persist block {block.get('index')}: {e}")

    def load_chain_from_db(self):
        def load_blocks():
            return list(blocks_col.find({}, {"_id": 0}).sort("index", ASCENDING))
        
        try:
            self.chain = safe_mongo_operation(load_blocks) or []
            logger.info(f"Loaded {len(self.chain)} blocks from database")
            
            # If no blocks, ensure we start fresh
            if not self.chain:
                logger.info("No blocks found, will create genesis block")
                
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
        if os.environ.get("RENDER") == "true":
            peer_url = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
        else:
            peer_url = f"http://{host}:{p}"
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

@app.route('/encryption-key')
def get_encryption_key():
    """Provide the encryption key hex to client for consistent encryption/decryption"""
    logger.debug("Encryption key requested")
    return {"key": ENCRYPTION_KEY_HEX}

# Debug endpoint removed for production security

# Socket.IO Events
@socketio.on('connect')
def handle_connect(auth=None):
    init_mongo()
    logger.debug("Client connected")
    emit("status", {"message": "Connected"})
    def get_recent_messages():
        return list(messages_col.find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(20))
    
    try:
        # Send recent messages (stored encrypted in DB)
        recent = safe_mongo_operation(get_recent_messages) or []
        if recent:
            for m in reversed(recent):
                try:
                    m['timestamp'] = float(m['timestamp'])
                    logger.debug(f"Sending recent encrypted message: {m['msg_id']}")
                    emit("message", m)
                except Exception as msg_error:
                    logger.error(f"Error sending message {m.get('msg_id', 'unknown')}: {msg_error}")
        else:
            logger.info("No recent messages found in database")
    except Exception as e:
        logger.error(f"Failed to send recent messages: {e}")
        # Send a system message instead of an error status
        try:
            error_encrypted = encrypt_message("Starting fresh! Your new messages will be encrypted and secure. 🔒✨")
            if error_encrypted:
                emit("message", {
                    "user_id": "System",
                    "message": error_encrypted,
                    "msg_id": str(uuid.uuid4()),
                    "type": "text",
                    "timestamp": time.time()
                })
        except:
            pass
    
    # Send welcome message
    try:
        welcome_encrypted = encrypt_message("Welcome to Chatify! 🚀 Your connection is secure and encrypted.")
        if welcome_encrypted:
            emit("message", {
                "user_id": "System",
                "message": welcome_encrypted,
                "msg_id": str(uuid.uuid4()),
                "type": "text",
                "timestamp": time.time()
            })
    except Exception as e:
        logger.error(f"Failed to send welcome message: {e}")

@socketio.on("disconnect")
def handle_disconnect():
    logger.debug("Client disconnected")

@socketio.on("join")
def handle_join(username):
    logger.info(f"User joined: {username}")
    try:
        join_encrypted = encrypt_message(f"{username} joined the chat 👋")
        if join_encrypted:
            emit("message", {
                "user_id": "System",
                "message": join_encrypted,
                "msg_id": str(uuid.uuid4()),
                "type": "text",
                "timestamp": time.time()
            }, broadcast=True)
        else:
            logger.error(f"Failed to encrypt join message for {username}")
    except Exception as e:
        logger.error(f"Error in join handler for {username}: {e}")

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
    encrypted_msg = data.get("message", "")
    msg_id = data.get("msg_id", str(uuid.uuid4()))
    msg_type = data.get("type", "text")
    filename = data.get("filename", "")
    ts = float(data.get("timestamp", time.time()))

    # Prevent duplicate processing
    if msg_id in processed_messages:
        logger.debug(f"Duplicate message {msg_id} ignored")
        return
    processed_messages.add(msg_id)

    # Validate encrypted message
    if not encrypted_msg:
        logger.error(f"Empty encrypted message from {user_id}")
        emit("status", {"message": "Invalid message received"})
        return

    # Decrypt for blockchain storage (blockchain needs readable content)
    decrypted_msg = decrypt_message(encrypted_msg)
    if decrypted_msg is None:
        logger.error(f"Decryption failed for message {msg_id} from {user_id}")
        emit("status", {"message": "Error decrypting message"})
        return

    logger.debug(f"Processing {msg_type} from {user_id}, ID: {msg_id}")

    # Store ENCRYPTED message in MongoDB for P2P security
    def store_message():
        messages_col.insert_one({
            "user_id": user_id,
            "message": encrypted_msg,  # Store encrypted for security
            "msg_id": msg_id,
            "type": msg_type,
            "filename": filename,
            "timestamp": ts
        })
    
    try:
        safe_mongo_operation(store_message)
        logger.debug(f"Encrypted message {msg_id} stored securely")
    except Exception as e:
        logger.error(f"Message storage failed for {msg_id}: {e}")
        # Continue execution even if storage fails
        logger.info("Continuing with message processing despite storage failure")

    # Add decrypted content to blockchain for integrity verification
    if not blockchain.add_transaction(user_id, decrypted_msg, msg_type, filename, ts):
        logger.error(f"Failed to add transaction for {msg_id}: Message too large")
        emit("status", {"message": "Message too large"})
        return

    # Mine block
    blockchain.async_mine_block()

    # Broadcast encrypted message to all connected clients
    msg_data = {
        "user_id": user_id,
        "message": encrypted_msg,
        "msg_id": msg_id,
        "type": msg_type,
        "filename": filename,
        "timestamp": ts
    }
    
    logger.debug(f"Broadcasting encrypted message: {msg_id}")
    emit("message", msg_data, broadcast=True, include_self=False)

    # Forward to P2P peers
    for client in peer_clients:
        try:
            client.emit("message", msg_data)
            logger.debug("Forwarded encrypted message to peer")
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
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    peer_ports = load_peers() or []
    local_ip = get_local_ip()
    
    # Detect production environment
    is_production = (
        os.environ.get("RENDER") == "true" or 
        os.environ.get("RAILWAY_ENVIRONMENT") == "production" or
        "onrender.com" in os.environ.get("RENDER_EXTERNAL_URL", "") or
        MONGO_URI.startswith("mongodb+srv://")
    )
    
    debug_mode = not is_production
    logger.info(f"Starting server on http://0.0.0.0:{port} - Production: {is_production}")
    
    if peer_ports and not is_production:
        connect_to_peers(peer_ports, host=local_ip)
    
    socketio.run(app, host="0.0.0.0", port=port, debug=debug_mode, use_reloader=False)