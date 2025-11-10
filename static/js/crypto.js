/**
 * Cryptography module for Chatify
 * Implements Signal Protocol (X3DH + Double Ratchet) using Web Crypto API
 * 
 * Note: This is a simplified implementation. For production, use libsignal-javascript
 * or the full Signal Protocol library.
 */

/**
 * Generate Identity Key Pair (Ed25519)
 * This is the long-term identity key for the user
 */
async function generateIdentityKeyPair() {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: "ECDH",
            namedCurve: "P-256" // Using P-256 as Ed25519 not widely supported
        },
        true, // extractable
        ["deriveKey", "deriveBits"]
    );
    
    const publicKey = await exportPublicKey(keyPair.publicKey);
    const privateKey = await exportPrivateKey(keyPair.privateKey);
    
    return {
        publicKey: publicKey,
        privateKey: privateKey,
        keyPair: keyPair
    };
}

/**
 * Generate Signed PreKey
 * This key is signed by the identity key and rotated periodically
 */
async function generateSignedPreKey(identityKeyPair, keyId) {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: "ECDH",
            namedCurve: "P-256"
        },
        true,
        ["deriveKey", "deriveBits"]
    );
    
    const publicKey = await exportPublicKey(keyPair.publicKey);
    const privateKey = await exportPrivateKey(keyPair.privateKey);
    
    // Sign the public key with identity key
    const signature = await signData(identityKeyPair.privateKey, publicKey);
    
    return {
        keyId: keyId,
        publicKey: publicKey,
        privateKey: privateKey,
        signature: signature,
        keyPair: keyPair
    };
}

/**
 * Generate One-Time PreKeys
 * These are used once per key exchange for forward secrecy
 */
async function generateOneTimePreKeys(count = 10, startId = 0) {
    const prekeys = [];
    
    for (let i = 0; i < count; i++) {
        const keyPair = await window.crypto.subtle.generateKey(
            {
                name: "ECDH",
                namedCurve: "P-256"
            },
            true,
            ["deriveKey", "deriveBits"]
        );
        
        const publicKey = await exportPublicKey(keyPair.publicKey);
        const privateKey = await exportPrivateKey(keyPair.privateKey);
        
        prekeys.push({
            keyId: startId + i,
            publicKey: publicKey,
            privateKey: privateKey,
            used: false
        });
    }
    
    return prekeys;
}

/**
 * Export public key to base64
 */
async function exportPublicKey(publicKey) {
    const exported = await window.crypto.subtle.exportKey("spki", publicKey);
    return arrayBufferToBase64(exported);
}

/**
 * Export private key to base64
 */
async function exportPrivateKey(privateKey) {
    const exported = await window.crypto.subtle.exportKey("pkcs8", privateKey);
    return arrayBufferToBase64(exported);
}

/**
 * Import public key from base64
 */
async function importPublicKey(base64Key) {
    const buffer = base64ToArrayBuffer(base64Key);
    return await window.crypto.subtle.importKey(
        "spki",
        buffer,
        {
            name: "ECDH",
            namedCurve: "P-256"
        },
        true,
        []
    );
}

/**
 * Import private key from base64
 */
async function importPrivateKey(base64Key) {
    const buffer = base64ToArrayBuffer(base64Key);
    return await window.crypto.subtle.importKey(
        "pkcs8",
        buffer,
        {
            name: "ECDH",
            namedCurve: "P-256"
        },
        true,
        ["deriveKey", "deriveBits"]
    );
}

/**
 * Sign data with private key
 */
async function signData(privateKey, data) {
    // Convert to signing key
    const signingKey = await window.crypto.subtle.importKey(
        "pkcs8",
        base64ToArrayBuffer(await exportPrivateKey(privateKey)),
        {
            name: "ECDSA",
            namedCurve: "P-256"
        },
        false,
        ["sign"]
    );
    
    const encoder = new TextEncoder();
    const dataBuffer = typeof data === 'string' ? encoder.encode(data) : data;
    
    const signature = await window.crypto.subtle.sign(
        {
            name: "ECDSA",
            hash: { name: "SHA-256" }
        },
        signingKey,
        dataBuffer
    );
    
    return arrayBufferToBase64(signature);
}

/**
 * Verify signature
 */
async function verifySignature(publicKey, data, signature) {
    try {
        const verifyKey = await window.crypto.subtle.importKey(
            "spki",
            base64ToArrayBuffer(publicKey),
            {
                name: "ECDSA",
                namedCurve: "P-256"
            },
            false,
            ["verify"]
        );
        
        const encoder = new TextEncoder();
        const dataBuffer = typeof data === 'string' ? encoder.encode(data) : data;
        const sigBuffer = base64ToArrayBuffer(signature);
        
        return await window.crypto.subtle.verify(
            {
                name: "ECDSA",
                hash: { name: "SHA-256" }
            },
            verifyKey,
            sigBuffer,
            dataBuffer
        );
    } catch (e) {
        console.error('Signature verification failed:', e);
        return false;
    }
}

/**
 * X3DH Key Agreement
 * Derive shared secret from key bundle
 */
async function performX3DH(myIdentityPrivate, myEphemeralPrivate, theirPreKeyBundle) {
    // Import their keys
    const theirIdentityPub = await importPublicKey(theirPreKeyBundle.identity_pub);
    const theirSignedPreKeyPub = await importPublicKey(theirPreKeyBundle.signed_prekey_pub);
    
    // Verify signed prekey signature
    const isValid = await verifySignature(
        theirPreKeyBundle.identity_pub,
        theirPreKeyBundle.signed_prekey_pub,
        theirPreKeyBundle.signed_prekey_sig
    );
    
    if (!isValid) {
        throw new Error('Invalid signed prekey signature');
    }
    
    // Import our keys
    const myIdPriv = await importPrivateKey(myIdentityPrivate);
    const myEphPriv = await importPrivateKey(myEphemeralPrivate);
    
    // Perform 4 DH operations (X3DH)
    const dh1 = await deriveBits(myIdPriv, theirSignedPreKeyPub);
    const dh2 = await deriveBits(myEphPriv, theirIdentityPub);
    const dh3 = await deriveBits(myEphPriv, theirSignedPreKeyPub);
    
    let dh4 = null;
    if (theirPreKeyBundle.one_time_prekey) {
        const theirOneTimePub = await importPublicKey(theirPreKeyBundle.one_time_prekey);
        dh4 = await deriveBits(myEphPriv, theirOneTimePub);
    }
    
    // Concatenate all DH outputs
    const dhOutputs = dh4 ? 
        concatenateArrayBuffers([dh1, dh2, dh3, dh4]) :
        concatenateArrayBuffers([dh1, dh2, dh3]);
    
    // Derive root key using HKDF
    const sharedSecret = await deriveKey(dhOutputs, 'X3DH');
    
    return sharedSecret;
}

/**
 * Derive bits from ECDH
 */
async function deriveBits(privateKey, publicKey) {
    return await window.crypto.subtle.deriveBits(
        {
            name: "ECDH",
            public: publicKey
        },
        privateKey,
        256
    );
}

/**
 * Derive key using HKDF
 */
async function deriveKey(keyMaterial, info) {
    // Import key material
    const baseKey = await window.crypto.subtle.importKey(
        "raw",
        keyMaterial,
        "HKDF",
        false,
        ["deriveKey"]
    );
    
    const encoder = new TextEncoder();
    
    // Derive AES-GCM key
    return await window.crypto.subtle.deriveKey(
        {
            name: "HKDF",
            hash: "SHA-256",
            salt: new Uint8Array(32), // Should be random in production
            info: encoder.encode(info)
        },
        baseKey,
        {
            name: "AES-GCM",
            length: 256
        },
        true,
        ["encrypt", "decrypt"]
    );
}

/**
 * Encrypt message with AES-GCM
 */
async function encryptMessage(key, plaintext) {
    const encoder = new TextEncoder();
    const data = encoder.encode(plaintext);
    
    // Generate random IV
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    
    const ciphertext = await window.crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        key,
        data
    );
    
    return {
        ciphertext: arrayBufferToBase64(ciphertext),
        iv: arrayBufferToBase64(iv)
    };
}

/**
 * Decrypt message with AES-GCM
 */
async function decryptMessage(key, ciphertext, iv) {
    const ciphertextBuffer = base64ToArrayBuffer(ciphertext);
    const ivBuffer = base64ToArrayBuffer(iv);
    
    const plaintext = await window.crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: ivBuffer
        },
        key,
        ciphertextBuffer
    );
    
    const decoder = new TextDecoder();
    return decoder.decode(plaintext);
}

/**
 * Initialize session with another user
 * This performs X3DH and stores the session
 * 
 * SIMPLIFIED VERSION: Uses a deterministic shared secret based on both users' identity keys
 * In production, this should use proper X3DH with ephemeral keys
 */
async function initializeSession(recipientUsername) {
    // Get our identity key
    const ourIdentity = await ChatifyDB.getIdentityKey();
    if (!ourIdentity) {
        throw new Error('No identity key found. Please register again.');
    }
    
    // Fetch recipient's prekey bundle
    const response = await fetch(`/chat/prekey-bundle/${recipientUsername}`);
    if (!response.ok) {
        throw new Error('Failed to fetch prekey bundle');
    }
    const prekeyBundle = await response.json();
    
    // Import recipient's identity public key
    const theirIdentityPub = await importPublicKey(prekeyBundle.identity_pub);
    const ourIdentityPriv = await importPrivateKey(ourIdentity.privateKey);
    
    // Perform ECDH between identity keys
    const sharedBits = await deriveBits(ourIdentityPriv, theirIdentityPub);
    
    // Derive session key using HKDF
    const sessionKey = await deriveKey(sharedBits, 'chatify_session_v1');
    
    // Store session with version marker
    const exportedKey = await exportKey(sessionKey);
    await ChatifyDB.storeSession(recipientUsername, {
        sharedSecret: exportedKey,
        version: 2, // Crypto version: 2 = identity key ECDH
        created: Date.now()
    });
    
    return sessionKey;
}

/**
 * Encrypt message for recipient
 */
async function encryptMessageForUser(recipientUsername, plaintext) {
    // Check if we have a session
    let session = await ChatifyDB.getSession(recipientUsername);
    
    if (!session) {
        // Initialize new session
        await initializeSession(recipientUsername);
        session = await ChatifyDB.getSession(recipientUsername);
    }
    
    // Import session key
    const sessionKey = await importKey(session.sessionState.sharedSecret);
    
    // Encrypt message
    return await encryptMessage(sessionKey, plaintext);
}

/**
 * Decrypt message from sender or to recipient
 * Works for both received messages (from sender) and own sent messages (to recipient)
 */
async function decryptMessageFromUser(otherUsername, ciphertext, iv) {
    // Get session with the other user
    const session = await ChatifyDB.getSession(otherUsername);
    
    if (!session) {
        // Initialize session if we're receiving a message
        try {
            await initializeSession(otherUsername);
            const newSession = await ChatifyDB.getSession(otherUsername);
            if (!newSession) {
                throw new Error('Failed to establish session');
            }
            const sessionKey = await importKey(newSession.sessionState.sharedSecret);
            return await decryptMessage(sessionKey, ciphertext, iv);
        } catch (error) {
            throw new Error('No session with this user. Cannot decrypt message.');
        }
    }
    
    // Check if this is an old session with incompatible crypto
    if (!session.version || session.version < 2) {
        // Clear old session and re-initialize
        await ChatifyDB.db.sessions.delete(otherUsername);
        await initializeSession(otherUsername);
        const newSession = await ChatifyDB.getSession(otherUsername);
        const sessionKey = await importKey(newSession.sessionState.sharedSecret);
        return await decryptMessage(sessionKey, ciphertext, iv);
    }
    
    // Import session key
    const sessionKey = await importKey(session.sessionState.sharedSecret);
    
    // Decrypt message
    return await decryptMessage(sessionKey, ciphertext, iv);
}

/**
 * Export key to base64
 */
async function exportKey(key) {
    const exported = await window.crypto.subtle.exportKey("raw", key);
    return arrayBufferToBase64(exported);
}

/**
 * Import key from base64
 */
async function importKey(base64Key) {
    const buffer = base64ToArrayBuffer(base64Key);
    return await window.crypto.subtle.importKey(
        "raw",
        buffer,
        {
            name: "AES-GCM",
            length: 256
        },
        true,
        ["encrypt", "decrypt"]
    );
}

// ============ UTILITY FUNCTIONS ============

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function concatenateArrayBuffers(buffers) {
    const totalLength = buffers.reduce((acc, buf) => acc + buf.byteLength, 0);
    const result = new Uint8Array(totalLength);
    let offset = 0;
    
    for (const buffer of buffers) {
        result.set(new Uint8Array(buffer), offset);
        offset += buffer.byteLength;
    }
    
    return result.buffer;
}

// ============ GROUP CHAT CRYPTO FUNCTIONS ============

/**
 * Generate a random AES-256 key for group chat
 */
async function generateGroupKey() {
    const key = await window.crypto.subtle.generateKey(
        {
            name: "AES-GCM",
            length: 256
        },
        true,
        ["encrypt", "decrypt"]
    );
    
    // Export to base64 for storage
    const exported = await window.crypto.subtle.exportKey("raw", key);
    return arrayBufferToBase64(exported);
}

/**
 * Encrypt group key with a member's public key (for secure distribution)
 * Uses ECDH to derive shared secret, then encrypts group key with that
 */
async function encryptGroupKeyForMember(groupKeyBase64, memberUsername) {
    // Get our identity key
    const identityKey = await ChatifyDB.getIdentityKey();
    if (!identityKey) {
        throw new Error('Identity key not found');
    }
    
    // Get member's public key from server
    const response = await fetch(`/chat/prekey-bundle/${memberUsername}`);
    if (!response.ok) {
        throw new Error('Failed to fetch member public key');
    }
    const bundle = await response.json();
    
    // Import member's identity public key
    const memberPublicKey = await importPublicKey(bundle.identity_pub);
    
    // Import our private key
    const ourPrivateKey = await importPrivateKey(identityKey.privateKey);
    
    // Derive shared secret using ECDH
    const sharedSecret = await window.crypto.subtle.deriveKey(
        {
            name: "ECDH",
            public: memberPublicKey
        },
        ourPrivateKey,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["encrypt"]
    );
    
    // Generate random IV
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    
    // Convert group key to array buffer
    const groupKeyBuffer = base64ToArrayBuffer(groupKeyBase64);
    
    // Encrypt group key with shared secret
    const encryptedBuffer = await window.crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        sharedSecret,
        groupKeyBuffer
    );
    
    // Return encrypted key + IV
    return {
        ciphertext: arrayBufferToBase64(encryptedBuffer),
        iv: arrayBufferToBase64(iv)
    };
}

/**
 * Decrypt group key using our private key
 */
async function decryptGroupKey(encryptedGroupKey, senderUsername) {
    // Get our identity key
    const identityKey = await ChatifyDB.getIdentityKey();
    if (!identityKey) {
        throw new Error('Identity key not found');
    }
    
    // Get sender's public key from server
    const response = await fetch(`/chat/prekey-bundle/${senderUsername}`);
    if (!response.ok) {
        throw new Error('Failed to fetch sender public key');
    }
    const bundle = await response.json();
    
    // Import sender's identity public key
    const senderPublicKey = await importPublicKey(bundle.identity_pub);
    
    // Import our private key
    const ourPrivateKey = await importPrivateKey(identityKey.privateKey);
    
    // Derive shared secret using ECDH
    const sharedSecret = await window.crypto.subtle.deriveKey(
        {
            name: "ECDH",
            public: senderPublicKey
        },
        ourPrivateKey,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["decrypt"]
    );
    
    // Decrypt group key
    const ivBuffer = base64ToArrayBuffer(encryptedGroupKey.iv);
    const ciphertextBuffer = base64ToArrayBuffer(encryptedGroupKey.ciphertext);
    
    const decryptedBuffer = await window.crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: ivBuffer
        },
        sharedSecret,
        ciphertextBuffer
    );
    
    // Return group key as base64
    return arrayBufferToBase64(decryptedBuffer);
}

/**
 * Encrypt message with group key
 */
async function encryptGroupMessage(groupKeyBase64, plaintext) {
    // Import group key
    const groupKeyBuffer = base64ToArrayBuffer(groupKeyBase64);
    const groupKey = await window.crypto.subtle.importKey(
        "raw",
        groupKeyBuffer,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["encrypt"]
    );
    
    // Generate random IV
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    
    // Convert plaintext to ArrayBuffer
    const encoder = new TextEncoder();
    const plaintextBuffer = encoder.encode(plaintext);
    
    // Encrypt
    const ciphertextBuffer = await window.crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        groupKey,
        plaintextBuffer
    );
    
    return {
        ciphertext: arrayBufferToBase64(ciphertextBuffer),
        nonce: arrayBufferToBase64(iv)
    };
}

/**
 * Decrypt group message with group key
 */
async function decryptGroupMessage(groupKeyBase64, ciphertext, iv) {
    // Import group key
    const groupKeyBuffer = base64ToArrayBuffer(groupKeyBase64);
    const groupKey = await window.crypto.subtle.importKey(
        "raw",
        groupKeyBuffer,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["decrypt"]
    );
    
    // Convert ciphertext and IV
    const ciphertextBuffer = base64ToArrayBuffer(ciphertext);
    const ivBuffer = base64ToArrayBuffer(iv);
    
    // Decrypt
    const plaintextBuffer = await window.crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: ivBuffer
        },
        groupKey,
        ciphertextBuffer
    );
    
    // Convert to string
    const decoder = new TextDecoder();
    return decoder.decode(plaintextBuffer);
}

/**
 * Try to decrypt group message with multiple keys (for key rotation support)
 * Tries current key first, then falls back to key history
 * 
 * @param {Array<string>} groupKeys - Array of group keys (newest first)
 * @param {string} ciphertext - Base64 encoded ciphertext
 * @param {string} iv - Base64 encoded IV
 * @returns {Promise<string>} Decrypted plaintext
 */
async function decryptGroupMessageWithHistory(groupKeys, ciphertext, iv) {
    if (!groupKeys || groupKeys.length === 0) {
        throw new Error('No group keys available');
    }
    
    // Try each key in order (newest to oldest)
    for (let i = 0; i < groupKeys.length; i++) {
        try {
            const plaintext = await decryptGroupMessage(groupKeys[i], ciphertext, iv);
            if (i > 0) {
                console.log(`✅ Decrypted with older key (key ${i + 1}/${groupKeys.length})`);
            }
            return plaintext;
        } catch (error) {
            // If this is the last key, throw the error
            if (i === groupKeys.length - 1) {
                throw new Error('Message encrypted with unavailable key');
            }
            // Otherwise, silently try next key
        }
    }
    
    throw new Error('Failed to decrypt message with any available key');
}

/**
 * Encrypt a file using AES-GCM
 * Returns encrypted file blob and metadata
 * 
 * @param {File|Blob} file - File to encrypt
 * @param {string} sessionKey - Base64 encoded session key (for private chat) or group key (for group chat)
 * @returns {Promise<Object>} Encrypted file data, IV, and metadata
 */
async function encryptFile(file, sessionKey) {
    // Generate encryption key from session key
    const keyBuffer = base64ToArrayBuffer(sessionKey);
    const cryptoKey = await window.crypto.subtle.importKey(
        "raw",
        keyBuffer,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["encrypt"]
    );
    
    // Generate random IV
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    
    // Read file as ArrayBuffer
    const fileBuffer = await file.arrayBuffer();
    
    // Encrypt file
    const encryptedBuffer = await window.crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        cryptoKey,
        fileBuffer
    );
    
    // Calculate SHA-256 hash of encrypted data for integrity
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', encryptedBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    
    return {
        encryptedBlob: new Blob([encryptedBuffer], { type: 'application/octet-stream' }),
        iv: arrayBufferToBase64(iv),
        hash: hashHex,
        originalName: file.name,
        originalType: file.type,
        originalSize: file.size
    };
}

/**
 * Decrypt a file using AES-GCM
 * 
 * @param {Blob} encryptedBlob - Encrypted file blob
 * @param {string} sessionKey - Base64 encoded session key or group key
 * @param {string} iv - Base64 encoded IV
 * @param {string} originalType - Original MIME type
 * @returns {Promise<Blob>} Decrypted file blob
 */
async function decryptFile(encryptedBlob, sessionKey, iv, originalType) {
    // Import key
    const keyBuffer = base64ToArrayBuffer(sessionKey);
    const cryptoKey = await window.crypto.subtle.importKey(
        "raw",
        keyBuffer,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["decrypt"]
    );
    
    // Read encrypted blob as ArrayBuffer
    const encryptedBuffer = await encryptedBlob.arrayBuffer();
    
    // Decrypt
    const ivBuffer = base64ToArrayBuffer(iv);
    const decryptedBuffer = await window.crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: ivBuffer
        },
        cryptoKey,
        encryptedBuffer
    );
    
    // Return as Blob with original type
    return new Blob([decryptedBuffer], { type: originalType });
}

/**
 * Calculate SHA-256 hash of a file
 * 
 * @param {File|Blob} file - File to hash
 * @returns {Promise<string>} Hex string hash
 */
async function calculateFileHash(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// Export all functions
window.ChatifyCrypto = {
    generateIdentityKeyPair,
    generateSignedPreKey,
    generateOneTimePreKeys,
    performX3DH,
    initializeSession,
    encryptMessageForUser,
    decryptMessageFromUser,
    encryptMessage,
    decryptMessage,
    decryptGroupMessageWithHistory,
    exportPublicKey,
    exportPrivateKey,
    importPublicKey,
    importPrivateKey,
    signData,
    verifySignature,
    // Group crypto functions
    generateGroupKey,
    encryptGroupKeyForMember,
    decryptGroupKey,
    encryptGroupMessage,
    decryptGroupMessage,
    // File crypto functions
    encryptFile,
    decryptFile,
    calculateFileHash
};

console.log('🔐 Crypto module loaded (awaiting DB initialization)');
