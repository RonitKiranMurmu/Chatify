# Chatify API Documentation

## Overview
This document provides comprehensive documentation for all REST and Socket.IO APIs in Chatify.

**Base URL:** `http://localhost:5000`  
**Authentication:** Session-based (cookies)  
**Content-Type:** `application/json`

---

## Authentication API

### POST /auth/register
Register a new user with public keys.

**Request Body:**
```json
{
  "username": "alice",
  "password": "SecurePass123",
  "identity_pub": "<base64_encoded_identity_public_key>",
  "signed_prekey_pub": "<base64_encoded_signed_prekey>",
  "signed_prekey_sig": "<base64_encoded_signature>",
  "one_time_prekeys": [
    {
      "id": "opk_001",
      "publicKey": "<base64_encoded_one_time_prekey>"
    }
  ]
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Registration successful",
  "user_id": "507f1f77bcf86cd799439011",
  "username": "alice"
}
```

**Errors:**
- `400` - Invalid input (username/password validation failed)
- `400` - Username already exists
- `500` - Server error

---

### POST /auth/login
Authenticate user and create session.

**Request Body:**
```json
{
  "username": "alice",
  "password": "SecurePass123"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "username": "alice"
}
```

**Errors:**
- `401` - Invalid credentials
- `500` - Server error

---

### POST /auth/logout
End user session.

**Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Chat API

### GET /chat/
Main chat interface (requires authentication).

**Response:** HTML page

---

### GET /chat/history/:chat_id
Get chat message history between two users.

**Parameters:**
- `chat_id` (path): Sorted usernames joined with `_` (e.g., `alice_bob`)
- `limit` (query): Max messages to return (default: 50)
- `skip` (query): Skip N messages (pagination, default: 0)

**Response (200):**
```json
{
  "messages": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "chat_id": "alice_bob",
      "sender": "alice",
      "recipient": "bob",
      "ciphertext": "<encrypted_message>",
      "nonce": "<nonce>",
      "ephemeral_pub": "<ephemeral_public_key>",
      "type": "text",
      "timestamp": "2025-11-10T12:00:00.000Z",
      "metadata": {
        "delivered": true,
        "read": false,
        "reactions": []
      }
    }
  ]
}
```

---

### GET /chat/users
Get list of all users (excluding self).

**Response (200):**
```json
{
  "users": [
    {
      "id": "507f1f77bcf86cd799439011",
      "username": "bob",
      "is_online": true,
      "last_seen": "2025-11-10T12:00:00.000Z"
    }
  ]
}
```

---

### GET /chat/prekey-bundle/:username
Get user's public key bundle for establishing encrypted session.

**Parameters:**
- `username` (path): Target user's username

**Response (200):**
```json
{
  "username": "bob",
  "identity_pub": "<base64_identity_public_key>",
  "signed_prekey_pub": "<base64_signed_prekey>",
  "signed_prekey_sig": "<base64_signature>",
  "one_time_prekey": "<base64_one_time_prekey>"
}
```

**Note:** One-time prekey is consumed after retrieval.

---

### POST /chat/upload-prekeys
Upload new one-time prekeys (for key rotation).

**Request Body:**
```json
{
  "one_time_prekeys": [
    {
      "id": "opk_100",
      "publicKey": "<base64_encoded_key>"
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "count": 10
}
```

---

### POST /chat/message/react/:message_id
Add emoji reaction to a message.

**Parameters:**
- `message_id` (path): Message ID

**Request Body:**
```json
{
  "emoji": "👍"
}
```

**Response (200):**
```json
{
  "success": true
}
```

---

### DELETE /chat/message/delete/:message_id
Delete a message (sender only).

**Parameters:**
- `message_id` (path): Message ID

**Response (200):**
```json
{
  "success": true
}
```

---

## Group Chat API

### POST /group/create
Create a new group.

**Request Body:**
```json
{
  "name": "Study Group",
  "members": ["bob", "charlie"],
  "encrypted_group_keys": {
    "bob": {
      "ciphertext": "<encrypted_group_key_for_bob>",
      "iv": "<initialization_vector>"
    },
    "charlie": {
      "ciphertext": "<encrypted_group_key_for_charlie>",
      "iv": "<initialization_vector>"
    }
  }
}
```

**Response (201):**
```json
{
  "group_id": "507f1f77bcf86cd799439011",
  "name": "Study Group",
  "admin": "alice",
  "members": ["alice", "bob", "charlie"],
  "created_at": "2025-11-10T12:00:00.000Z"
}
```

---

### GET /group/list
Get all groups where user is a member.

**Response (200):**
```json
{
  "groups": [
    {
      "group_id": "507f1f77bcf86cd799439011",
      "name": "Study Group",
      "admin": "alice",
      "members": ["alice", "bob", "charlie"],
      "created_at": "2025-11-10T12:00:00.000Z"
    }
  ]
}
```

---

### GET /group/:group_id
Get group details.

**Parameters:**
- `group_id` (path): Group ID

**Response (200):**
```json
{
  "group_id": "507f1f77bcf86cd799439011",
  "name": "Study Group",
  "admin": "alice",
  "members": ["alice", "bob", "charlie"],
  "encrypted_group_key": {
    "ciphertext": "<encrypted_group_key>",
    "iv": "<initialization_vector>"
  },
  "created_at": "2025-11-10T12:00:00.000Z"
}
```

---

### GET /group/:group_id/history
Get group message history.

**Parameters:**
- `group_id` (path): Group ID
- `limit` (query): Max messages (default: 50)
- `skip` (query): Skip N messages (default: 0)

**Response (200):**
```json
{
  "messages": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "group_id": "507f1f77bcf86cd799439011",
      "sender": "alice",
      "ciphertext": "<encrypted_message>",
      "nonce": "<nonce>",
      "type": "text",
      "timestamp": "2025-11-10T12:00:00.000Z",
      "metadata": {
        "reactions": []
      }
    }
  ]
}
```

---

### POST /group/:group_id/add-member
Add a member to group (admin only).

**Request Body:**
```json
{
  "username": "david",
  "encrypted_group_key": {
    "ciphertext": "<encrypted_group_key_for_david>",
    "iv": "<initialization_vector>"
  }
}
```

**Response (200):**
```json
{
  "success": true
}
```

**Errors:**
- `403` - Not admin
- `400` - User already in group

---

### POST /group/:group_id/remove-member
Remove a member from group (admin only).

**Request Body:**
```json
{
  "username": "charlie",
  "new_encrypted_keys": {
    "bob": {
      "ciphertext": "<new_encrypted_group_key>",
      "iv": "<initialization_vector>"
    }
  }
}
```

**Response (200):**
```json
{
  "success": true
}
```

**Note:** Generates new group key and re-encrypts for remaining members.

---

### POST /group/:group_id/leave
Leave a group.

**Response (200):**
```json
{
  "success": true
}
```

**Note:** If admin leaves, admin is transferred to another member.

---

## File Upload API

### POST /file/upload
Upload encrypted file.

**Request:** Multipart form data
- `file`: File binary
- `file_metadata`: JSON string with:
  ```json
  {
    "chat_id": "alice_bob",
    "recipient": "bob",
    "iv": "<initialization_vector>",
    "file_hash": "<sha256_hash>"
  }
  ```

**Response (201):**
```json
{
  "file_id": "507f1f77bcf86cd799439011",
  "filename": "document.pdf",
  "size": 102400,
  "upload_date": "2025-11-10T12:00:00.000Z"
}
```

**Limits:**
- Max file size: 16MB
- Allowed types: images, videos, audio, documents

---

### GET /file/download/:file_id
Download encrypted file.

**Parameters:**
- `file_id` (path): File ID

**Response:** File binary with headers:
```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="document.pdf"
```

---

### GET /file/info/:file_id
Get file metadata.

**Response (200):**
```json
{
  "file_id": "507f1f77bcf86cd799439011",
  "filename": "document.pdf",
  "size": 102400,
  "content_type": "application/pdf",
  "upload_date": "2025-11-10T12:00:00.000Z",
  "sender": "alice",
  "recipient": "bob"
}
```

---

## Server Chat API

### GET /server-chat/messages
Get recent server-wide chat messages.

**Parameters:**
- `limit` (query): Max messages (default: 100)

**Response (200):**
```json
{
  "messages": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "sender": "alice",
      "text": "Hello everyone!",
      "timestamp": "2025-11-10T12:00:00.000Z",
      "reactions": {
        "👍": ["bob", "charlie"]
      }
    }
  ]
}
```

---

## Socket.IO Events

### Client → Server Events

#### `send_message`
Send encrypted private message.

**Data:**
```json
{
  "chat_id": "alice_bob",
  "recipient": "bob",
  "ciphertext": "<encrypted_message>",
  "nonce": "<nonce>",
  "ephemeral_pub": "<ephemeral_public_key>",
  "type": "text",
  "timestamp": "2025-11-10T12:00:00.000Z",
  "metadata": {
    "reply_to": "message_id",
    "reply_to_user": "bob",
    "reply_to_content": "Original message"
  }
}
```

---

#### `send_group_message`
Send encrypted group message.

**Data:**
```json
{
  "group_id": "507f1f77bcf86cd799439011",
  "ciphertext": "<encrypted_message>",
  "nonce": "<nonce>",
  "type": "text",
  "timestamp": "2025-11-10T12:00:00.000Z"
}
```

---

#### `send_server_message`
Send plain text to server chat.

**Data:**
```json
{
  "text": "Hello everyone!"
}
```

---

#### `typing_start` / `typing_stop`
Notify typing status.

**Data:**
```json
{
  "recipient": "bob"
}
```

---

### Server → Client Events

#### `receive_message`
Receive encrypted private message.

**Data:** Same as `send_message`

---

#### `receive_group_message`
Receive encrypted group message.

**Data:** Same as `send_group_message`

---

#### `receive_server_message`
Receive server chat message.

**Data:**
```json
{
  "message_id": "507f1f77bcf86cd799439011",
  "sender": "alice",
  "text": "Hello!",
  "timestamp": "2025-11-10T12:00:00.000Z"
}
```

---

#### `user_status`
User online/offline status change.

**Data:**
```json
{
  "username": "bob",
  "status": "online"
}
```

---

#### `user_typing`
User typing indicator.

**Data:**
```json
{
  "username": "bob",
  "typing": true
}
```

---

#### `message_status_update`
Message delivery/read status.

**Data:**
```json
{
  "message_id": "507f1f77bcf86cd799439011",
  "status": "delivered"
}
```

---

#### `message_deleted`
Message deletion notification.

**Data:**
```json
{
  "message_id": "507f1f77bcf86cd799439011",
  "chat_id": "alice_bob"
}
```

---

#### `group_notification`
Group membership change notification.

**Data:**
```json
{
  "group_id": "507f1f77bcf86cd799439011",
  "type": "member_added",
  "username": "david"
}
```

---

## Error Responses

All endpoints may return these error codes:

- `400` - Bad Request (invalid input)
- `401` - Unauthorized (not authenticated)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

**Error Format:**
```json
{
  "error": "Error message description"
}
```

---

## Rate Limiting

Currently no rate limiting implemented. For production:
- Consider limiting: 100 requests/minute per user
- WebSocket events: 50 messages/minute

---

## Security Notes

1. All REST API calls should use HTTPS in production
2. Socket.IO connections should use WSS (secure WebSockets)
3. Messages are end-to-end encrypted (except server chat)
4. Files are encrypted before upload
5. Session cookies are HTTP-only and secure in production

---

**Last Updated:** November 11, 2025  
**Version:** 1.0
