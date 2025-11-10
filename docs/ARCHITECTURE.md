# Chatify - System Architecture

## Overview

Chatify is a **hybrid decentralized chat application** that uses **end-to-end encryption** (E2EE) with the Signal Protocol. The server acts as a **key broker and message relay**, never seeing plaintext message content.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐        ┌──────────────┐       ┌─────────────┐│
│  │   Browser    │        │  IndexedDB   │       │ libsignal   ││
│  │ (UI/React)   │◄──────►│ (Private Keys)│◄─────►│ (Crypto)    ││
│  └──────────────┘        └──────────────┘       └─────────────┘│
└────────────┬────────────────────────────────────────────────────┘
             │
             │ HTTPS / WSS (Encrypted Transport)
             │
┌────────────▼────────────────────────────────────────────────────┐
│                        SERVER LAYER                              │
│  ┌──────────────┐   ┌───────────────┐    ┌──────────────────┐  │
│  │    Flask     │   │ Flask-SocketIO │    │   Key Exchange   │  │
│  │  (REST API)  │◄─►│  (WebSocket)   │◄──►│      API         │  │
│  └──────────────┘   └───────────────┘    └──────────────────┘  │
└────────────┬────────────────────────────────────────────────────┘
             │
             │
┌────────────▼────────────────────────────────────────────────────┐
│                      DATABASE LAYER                              │
│         ┌──────────────────────────────────────┐                 │
│         │          MongoDB Atlas               │                 │
│         │  ┌────────────┐  ┌─────────────┐    │                 │
│         │  │   Users    │  │  Messages   │    │                 │
│         │  │ (Public    │  │ (Encrypted) │    │                 │
│         │  │   Keys)    │  └─────────────┘    │                 │
│         │  └────────────┘  ┌─────────────┐    │                 │
│         │  ┌────────────┐  │   Groups    │    │                 │
│         │  │   Files    │  │ (Encrypted) │    │                 │
│         │  │ (GridFS)   │  └─────────────┘    │                 │
│         │  └────────────┘                      │                 │
│         └──────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. User Registration
```
┌─────────┐                                    ┌─────────┐
│ Client  │                                    │ Server  │
│  (Bob)  │                                    │         │
└────┬────┘                                    └────┬────┘
     │                                               │
     │ 1. Generate Keys (IK, SPK, OPKs)             │
     │    using libsignal                            │
     │                                               │
     │ 2. POST /auth/register                        │
     │    { username, password_hash,                 │
     │      identity_pub, signed_prekey_pub,         │
     │      one_time_prekeys[] }                     │
     ├──────────────────────────────────────────────►│
     │                                               │
     │                                               │ 3. Hash password (bcrypt)
     │                                               │    Store user + public keys
     │                                               │    in MongoDB
     │                                               │
     │ 4. 201 Created                                │
     │    { success: true, user_id, username }       │
     │◄──────────────────────────────────────────────┤
     │                                               │
     │ 5. Store private keys in IndexedDB            │
     │    (browser local storage)                    │
     │                                               │
```

### 2. Message Sending (E2E Encrypted)
```
┌─────────┐         ┌─────────┐         ┌─────────┐
│ Alice   │         │ Server  │         │  Bob    │
└────┬────┘         └────┬────┘         └────┬────┘
     │                   │                    │
     │ 1. GET /keys/bob  │                    │
     ├──────────────────►│                    │
     │                   │                    │
     │ 2. Return Bob's   │                    │
     │    public key     │                    │
     │    bundle         │                    │
     │◄──────────────────┤                    │
     │                   │                    │
     │ 3. Perform X3DH   │                    │
     │    key agreement  │                    │
     │    (libsignal)    │                    │
     │                   │                    │
     │ 4. Encrypt msg    │                    │
     │    with session   │                    │
     │    key            │                    │
     │                   │                    │
     │ 5. Socket: send   │                    │
     │    { ciphertext,  │                    │
     │      nonce,       │                    │
     │      ephemeral }  │                    │
     ├──────────────────►│                    │
     │                   │                    │
     │                   │ 6. Store encrypted │
     │                   │    message in DB   │
     │                   │                    │
     │                   │ 7. Forward to Bob  │
     │                   │    (if online)     │
     │                   ├───────────────────►│
     │                   │                    │
     │                   │                    │ 8. Decrypt with
     │                   │                    │    session key
     │                   │                    │    (libsignal)
     │                   │                    │
     │                   │ 9. Ack (delivered) │
     │                   │◄───────────────────┤
     │                   │                    │
     │ 10. Status update │                    │
     │◄──────────────────┤                    │
     │                   │                    │
```

---

## Component Details

### Frontend (Client)

#### Technologies
- **HTML5 + CSS3**: Structure and styling
- **Tailwind CSS**: Utility-first CSS framework
- **Vanilla JavaScript**: Client logic
- **Socket.IO Client**: Real-time communication
- **@signalapp/libsignal-client**: E2E encryption
- **Dexie.js**: IndexedDB wrapper for key storage

#### Responsibilities
- User interface rendering
- Key generation and management
- Message encryption/decryption
- Real-time event handling
- File encryption before upload
- Session state management

---

### Backend (Server)

#### Technologies
- **Flask**: Python web framework
- **Flask-SocketIO**: WebSocket support
- **Flask-CORS**: Cross-origin resource sharing
- **eventlet**: Async event handling

#### API Endpoints

**Authentication**
```
POST   /auth/register    - Create new user account
POST   /auth/login       - Authenticate user
POST   /auth/logout      - End user session
GET    /auth/check       - Verify session status
```

**Key Management**
```
GET    /keys/<username>        - Get user's public key bundle
POST   /keys/refresh-prekeys   - Upload new one-time prekeys
GET    /keys/verify/<username> - Get identity key fingerprint
```

**Chat**
```
GET    /chat/                     - Chat interface
GET    /chat/history/<chat_id>   - Get encrypted message history
GET    /chat/users               - Get list of users
POST   /chat/message/read/:id    - Mark message as read
POST   /chat/message/react/:id   - Add reaction to message
DELETE /chat/message/:id         - Delete message
```

**Files**
```
POST   /files/upload       - Upload encrypted file
GET    /files/download/:id - Download encrypted file
GET    /files/info/:id     - Get file metadata
```

#### Socket.IO Events

**Client → Server**
```javascript
'send_message'     // Send encrypted message
'typing_start'     // User started typing
'typing_stop'      // User stopped typing
'message_read'     // Message was read
'join_room'        // Join group chat room
'leave_room'       // Leave group chat room
```

**Server → Client**
```javascript
'receive_message'   // New message received
'message_sent'      // Message delivery confirmation
'user_status'       // User online/offline status
'user_typing'       // Typing indicator
'message_status'    // Read/delivered receipt update
'error'             // Error notification
```

---

### Database (MongoDB)

#### Collections

**users**
```javascript
{
  _id: ObjectId,
  username: String (unique, indexed),
  password_hash: String,
  identity_pub: String (base64),
  signed_prekey_pub: String (base64),
  signed_prekey_sig: String (base64),
  one_time_prekeys: [{
    id: String,
    key: String (base64),
    used: Boolean
  }],
  created_at: DateTime,
  last_seen: DateTime,
  is_online: Boolean
}
```

**messages**
```javascript
{
  _id: ObjectId,
  chat_id: String (indexed),
  sender: String (indexed),
  recipient: String (indexed),
  ciphertext: String (base64),
  nonce: String (base64),
  ephemeral_pub: String (base64),
  timestamp: DateTime (indexed),
  type: String (text/file/media),
  metadata: {
    read: Boolean,
    delivered: Boolean,
    reactions: [{user: String, emoji: String}],
    reply_to: ObjectId,
    edited: Boolean
  }
}
```

**groups**
```javascript
{
  _id: ObjectId,
  group_name: String,
  admin: String (indexed),
  members: [String] (indexed),
  group_key_encrypted: {
    username1: String (encrypted group key),
    username2: String (encrypted group key)
  },
  created_at: DateTime
}
```

---

## Security Architecture

### Encryption Layers

```
┌────────────────────────────────────────────────┐
│           APPLICATION LAYER                    │
│  User Interface (Plain text visible to user)  │
└────────────────┬───────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────┐
│          ENCRYPTION LAYER (Client)             │
│  ┌──────────────────────────────────────────┐ │
│  │   libsignal (Signal Protocol)            │ │
│  │   - X3DH Key Agreement                   │ │
│  │   - Double Ratchet Algorithm             │ │
│  │   - AES-256-GCM Encryption               │ │
│  └──────────────────────────────────────────┘ │
└────────────────┬───────────────────────────────┘
                 │ Ciphertext
                 ▼
┌────────────────────────────────────────────────┐
│       TRANSPORT LAYER (TLS/SSL)                │
│  HTTPS (Port 443) / WSS (WebSocket Secure)    │
└────────────────┬───────────────────────────────┘
                 │ Double Encrypted
                 ▼
┌────────────────────────────────────────────────┐
│           SERVER (Zero Knowledge)              │
│  Only sees encrypted ciphertext, never keys   │
└────────────────┬───────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────┐
│      DATABASE (Encrypted at Rest)              │
│  Ciphertext stored, plaintext never exists    │
└────────────────────────────────────────────────┘
```

### Key Exchange (X3DH Protocol)

```
Alice wants to send first message to Bob:

1. Alice retrieves Bob's prekey bundle from server:
   - Identity Key (IK_Bob)
   - Signed Prekey (SPK_Bob)
   - One-Time Prekey (OPK_Bob) [consumed]

2. Alice generates ephemeral key (EK_Alice)

3. Alice computes shared secrets:
   DH1 = ECDH(IK_Alice, SPK_Bob)
   DH2 = ECDH(EK_Alice, IK_Bob)
   DH3 = ECDH(EK_Alice, SPK_Bob)
   DH4 = ECDH(EK_Alice, OPK_Bob)  [if available]

4. Alice derives session key:
   SK = HKDF(DH1 || DH2 || DH3 || DH4)

5. Alice encrypts message:
   Ciphertext = AES-GCM(SK, plaintext, nonce)

6. Alice sends to Bob:
   { ciphertext, nonce, EK_Alice }

7. Bob receives and computes same SK using EK_Alice

8. Bob decrypts:
   Plaintext = AES-GCM-Decrypt(SK, ciphertext, nonce)
```

---

## File Storage Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLIENT                        │
│  1. Select file                                 │
│  2. Encrypt with AES-256 (random key)          │
│  3. Encrypt file key with recipient's pub key  │
│  4. Calculate SHA-256 hash                      │
└────────────────┬────────────────────────────────┘
                 │ Encrypted file
                 ▼
┌─────────────────────────────────────────────────┐
│                   SERVER                        │
│  Receive encrypted file + metadata              │
│  Validate size (max 16MB)                       │
│  Verify hash                                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              MongoDB GridFS                     │
│  Store file in chunks                           │
│  Metadata: {                                    │
│    file_id, filename, size, hash,               │
│    uploader, timestamp                          │
│  }                                              │
└─────────────────────────────────────────────────┘
```

---

## Scaling Considerations

### Horizontal Scaling
```
          ┌──── Load Balancer ────┐
          │                        │
    ┌─────▼─────┐           ┌─────▼─────┐
    │  Flask    │           │  Flask    │
    │  Server 1 │           │  Server 2 │
    └─────┬─────┘           └─────┬─────┘
          │                        │
          └──────────┬─────────────┘
                     │
              ┌──────▼──────┐
              │   MongoDB   │
              │   Cluster   │
              └─────────────┘
```

### Caching Strategy
- **Redis**: Session storage, online user tracking
- **CDN**: Static assets (CSS, JS, images)
- **Client**: IndexedDB for message cache

---

## Performance Optimizations

1. **Database Indexing**
   - Username (unique)
   - Chat_id + timestamp
   - Sender/recipient fields

2. **Message Pagination**
   - Load 50 messages at a time
   - Lazy load older messages on scroll

3. **Connection Pooling**
   - MongoDB connection pool
   - Socket.IO connection management

4. **Compression**
   - Gzip for HTTP responses
   - WebSocket message compression

---

## Security Measures

1. **Authentication**
   - bcrypt password hashing (12 rounds)
   - Secure session management
   - CSRF protection

2. **Transport Security**
   - HTTPS/TLS for all traffic
   - WSS for WebSocket connections
   - HSTS headers

3. **Input Validation**
   - Server-side validation
   - SQL injection prevention (MongoDB)
   - XSS protection

4. **Rate Limiting**
   - Login attempt throttling
   - Message send rate limits
   - API endpoint rate limits

---

## Monitoring & Logging

```python
# Application logs
- User registration/login events
- Message send/receive events
- Error tracking
- Performance metrics

# Security logs
- Failed login attempts
- Suspicious activities
- Key exchange events
```

---

This architecture ensures:
✅ **Security**: E2E encryption, zero-knowledge server  
✅ **Performance**: Optimized database, efficient caching  
✅ **Scalability**: Horizontal scaling ready  
✅ **Reliability**: Error handling, logging  
✅ **Privacy**: Server never sees plaintext  

---

*Last Updated: November 2025*
