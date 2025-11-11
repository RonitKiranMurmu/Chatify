# 🏗️ Chatify Deployment Architecture

## System Architecture Diagram

```
                                    USERS
                                      │
                                      │ HTTPS/WSS
                                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                        RENDER PLATFORM                           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Load Balancer + CDN                        │   │
│  │  • Free SSL/TLS Certificates                           │   │
│  │  • DDoS Protection                                     │   │
│  │  • Global Edge Network                                 │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│                       ↓                                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         Web Service (chatify-xxxx.onrender.com)        │   │
│  │                                                         │   │
│  │  ┌─────────────────────────────────────────────────┐  │   │
│  │  │           Gunicorn WSGI Server                  │  │   │
│  │  │  • Worker Class: gevent                         │  │   │
│  │  │  • Workers: 1 (for Socket.IO state)            │  │   │
│  │  │  • Port: $PORT (assigned by Render)            │  │   │
│  │  └────────────────┬────────────────────────────────┘  │   │
│  │                   │                                     │   │
│  │                   ↓                                     │   │
│  │  ┌─────────────────────────────────────────────────┐  │   │
│  │  │        Flask Application (app.py)               │  │   │
│  │  │                                                 │  │   │
│  │  │  Routes:                                        │  │   │
│  │  │  • / (Landing Page)                            │  │   │
│  │  │  • /register (User Registration)               │  │   │
│  │  │  • /login (Authentication)                     │  │   │
│  │  │  • /chat (Main Chat Interface)                 │  │   │
│  │  │  • /api/* (REST Endpoints)                     │  │   │
│  │  │  • /health (Health Check)                      │  │   │
│  │  └────────────────┬────────────────────────────────┘  │   │
│  │                   │                                     │   │
│  │                   ↓                                     │   │
│  │  ┌─────────────────────────────────────────────────┐  │   │
│  │  │        Flask-SocketIO (WebSocket)               │  │   │
│  │  │                                                 │  │   │
│  │  │  Events:                                        │  │   │
│  │  │  • connect/disconnect                          │  │   │
│  │  │  • send_message                                │  │   │
│  │  │  • receive_message                             │  │   │
│  │  │  • typing_start/stop                           │  │   │
│  │  │  • message_read                                │  │   │
│  │  └─────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  Environment:                                           │   │
│  │  • Python 3.11.0                                       │   │
│  │  • Dependencies from requirements.txt                  │   │
│  │  • Environment variables from Render UI                │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ MongoDB Atlas Connection
                        │ (mongodb+srv:// - TLS Encrypted)
                        │
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MONGODB ATLAS (Cloud)                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Cluster0 (Free Tier M0)                    │   │
│  │                                                         │   │
│  │  Database: chatify                                      │   │
│  │                                                         │   │
│  │  Collections:                                           │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  users                                           │  │   │
│  │  │  • username (unique)                             │  │   │
│  │  │  • password_hash (bcrypt)                        │  │   │
│  │  │  • identity_pub (public key)                     │  │   │
│  │  │  • signed_prekey_pub                             │  │   │
│  │  │  • one_time_prekeys[]                            │  │   │
│  │  │  • is_online, last_seen                          │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  messages                                        │  │   │
│  │  │  • chat_id                                       │  │   │
│  │  │  • sender, recipient                             │  │   │
│  │  │  • ciphertext (encrypted!)                       │  │   │
│  │  │  • nonce, ephemeral_pub                          │  │   │
│  │  │  • timestamp                                     │  │   │
│  │  │  • metadata (read, delivered, reactions)         │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  groups                                          │  │   │
│  │  │  • group_name                                    │  │   │
│  │  │  • admin, members[]                              │  │   │
│  │  │  • group_key_encrypted{}                         │  │   │
│  │  │  • created_at                                    │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  server_messages                                 │  │   │
│  │  │  • sender                                        │  │   │
│  │  │  • message (NOT encrypted - public chat)        │  │   │
│  │  │  • timestamp, reactions                          │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  Security:                                              │   │
│  │  • Network Access: 0.0.0.0/0 (allow all)              │   │
│  │  • TLS/SSL: Enabled                                    │   │
│  │  • Authentication: Username/Password                   │   │
│  │  • Backups: Automatic (Atlas)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘


                        CLIENT BROWSER
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      USER'S BROWSER                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Frontend (HTML/CSS/JS)                     │   │
│  │                                                         │   │
│  │  Files:                                                 │   │
│  │  • templates/*.html (Jinja2)                           │   │
│  │  • static/css/style.css (Tailwind)                     │   │
│  │  • static/js/crypto.js (Encryption)                    │   │
│  │  • static/js/db.js (IndexedDB)                         │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│                       ↓                                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         Web Crypto API (Browser Native)                │   │
│  │                                                         │   │
│  │  • Key Generation (ECDH P-256)                         │   │
│  │  • X3DH Key Agreement                                  │   │
│  │  • AES-GCM Encryption/Decryption                       │   │
│  │  • HKDF Key Derivation                                 │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│                       ↓                                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         IndexedDB (Local Storage)                       │   │
│  │                                                         │   │
│  │  Database: chatify-keys                                 │   │
│  │                                                         │   │
│  │  Stores:                                                │   │
│  │  • identityKey (PRIVATE - never leaves browser!)       │   │
│  │  • signedPreKey (PRIVATE)                              │   │
│  │  • oneTimePreKeys (PRIVATE)                            │   │
│  │  • sessions (shared secrets per contact)               │   │
│  │                                                         │   │
│  │  ⚠️ CRITICAL: Private keys NEVER transmitted!          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Sending an Encrypted Message

```
1. USER TYPES MESSAGE
   Alice types: "Hello Bob!"
        ↓

2. ENCRYPTION (Client-Side)
   crypto.js:
   • Load Alice's session with Bob from IndexedDB
   • If no session: Perform X3DH key agreement
     - Fetch Bob's public keys from server
     - Generate shared secret (ECDH)
     - Derive encryption key (HKDF)
     - Store session in IndexedDB
   • Encrypt plaintext with AES-GCM
     - Input: "Hello Bob!"
     - Output: ciphertext + nonce
        ↓

3. TRANSMISSION (WebSocket)
   Socket.IO emit('send_message'):
   {
     chat_id: 'alice_bob',
     recipient: 'bob',
     ciphertext: 'x7k9...' (base64),
     nonce: 'a3f2...' (base64),
     type: 'text'
   }
        ↓

4. SERVER RELAY (Zero-Knowledge)
   Flask-SocketIO (Render):
   • Receive encrypted payload
   • Store in MongoDB (ciphertext only!)
   • Forward to Bob if online
   • NEVER decrypts - has no keys!
        ↓

5. DATABASE STORAGE (MongoDB Atlas)
   messages collection:
   {
     _id: ObjectId(...),
     sender: 'alice',
     recipient: 'bob',
     ciphertext: 'x7k9...',  ← Gibberish!
     nonce: 'a3f2...',
     timestamp: ISODate(...)
   }
        ↓

6. RECEIVE (Bob's Browser)
   Socket.IO on('receive_message'):
   • Bob's browser receives encrypted payload
        ↓

7. DECRYPTION (Client-Side)
   crypto.js:
   • Load Bob's session with Alice from IndexedDB
   • Decrypt ciphertext with AES-GCM
     - Input: ciphertext + nonce
     - Output: "Hello Bob!"
   • Display plaintext in UI
        ↓

8. BOB SEES MESSAGE
   "Hello Bob!" ✅

   ⚠️ SERVER NEVER SAW "Hello Bob!" - Only ciphertext!
```

---

## Security Boundaries

```
┌────────────────────────────────────────────────────────────┐
│              TRUSTED ZONE (Client Browser)                  │
│                                                             │
│  • Private keys stored                                     │
│  • Plaintext messages visible                              │
│  • Encryption/Decryption happens here                      │
│  • User controls this zone                                 │
└────────────────────────────┬───────────────────────────────┘
                             │
                    ENCRYPTED CHANNEL
                     (HTTPS/WSS + E2E)
                             │
┌────────────────────────────┴───────────────────────────────┐
│            UNTRUSTED ZONE (Server + Database)               │
│                                                             │
│  • NO private keys                                         │
│  • Only ciphertext visible                                 │
│  • Cannot decrypt messages                                 │
│  • Render operators cannot read messages                   │
│  • Database admin cannot read messages                     │
│  • Even if database hacked: ciphertext useless!            │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Workflow

```
DEVELOPER MACHINE                    GITHUB                    RENDER
      │                                │                          │
      │                                │                          │
 1. Code changes                       │                          │
      │                                │                          │
 2. git add .                          │                          │
    git commit -m "..."                │                          │
      │                                │                          │
 3. git push origin optimized          │                          │
      └────────────────────────────────►                          │
                                       │                          │
                                  4. Webhook                      │
                                  triggers                        │
                                       └──────────────────────────►
                                                                  │
                                                          5. Auto-deploy
                                                             • Clone repo
                                                             • pip install
                                                             • Start Gunicorn
                                                                  │
                                                          6. Health check
                                                             GET /health
                                                                  │
                                                          7. Route traffic
                                                             to new instance
                                                                  │
                                                                 LIVE!
```

---

## Scaling Strategy

### Current (Free Tier)
```
┌─────────────────────┐
│   Render Instance   │
│   • 512MB RAM       │
│   • Shared CPU      │
│   • 1 Worker        │
│   • ~50 users       │
└─────────────────────┘
```

### Starter Plan ($7/month)
```
┌─────────────────────┐
│   Render Instance   │
│   • 1GB RAM         │
│   • Dedicated CPU   │
│   • 1 Worker        │
│   • ~200 users      │
└─────────────────────┘
```

### Production Scale (Standard $25/month)
```
┌─────────────────────┐     ┌─────────────────────┐
│  Render Instance 1  │     │  Render Instance 2  │
│   • 4GB RAM         │     │   • 4GB RAM         │
│   • 2 CPU cores     │     │   • 2 CPU cores     │
│   • 1 Worker        │     │   • 1 Worker        │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           └───────────┬───────────────┘
                       │
              ┌────────▼────────┐
              │  Load Balancer  │
              │   + Redis       │
              │  (for sessions) │
              └─────────────────┘
                       │
                    ~1000+ users
```

---

## Monitoring & Alerts

### Built-in Health Check
```
GET /health
→ 200 OK
{
  "status": "healthy",
  "service": "chatify"
}
```

### Render Dashboard Metrics
- CPU Usage %
- Memory Usage %
- HTTP Response Time
- Request Count
- Bandwidth

### Log Levels
```
INFO:  Normal operations
WARN:  Non-critical issues
ERROR: Application errors
DEBUG: Development only (disabled in production)
```

---

## Cost Optimization Tips

### Free Tier ($0/month)
✅ Perfect for:
- Portfolio demos
- College projects
- Low traffic apps
- Development/testing

⚠️ Limitations:
- Spins down after 15 min idle (15-30s cold start)
- 750 hours/month (use multiple services for 24/7)
- Shared resources

### When to Upgrade
Upgrade to Starter ($7/month) when:
- Cold starts affect user experience
- Need 24/7 availability
- Traffic > 1000 requests/day
- Professional use case

---

**Ready to deploy? Follow DEPLOYMENT_CHECKLIST.md!** ✅
