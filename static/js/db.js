/**
 * IndexedDB database wrapper using Dexie.js
 * Stores encryption keys, sessions, and local message cache
 * Each user gets their own namespaced database
 */

let db = null; // Will be initialized with username

/**
 * Initialize database for specific user
 */
function initDB(username) {
    if (!username) {
        throw new Error('Username required to initialize database');
    }
    
    // Create database with username-specific name
    db = new Dexie(`ChatifyDB_${username}`);
    
    // Define schema
    db.version(1).stores({
        // Identity keys and prekeys (private keys stored here)
        keys: 'id, type, publicKey, privateKey, timestamp',
        
        // Sessions with other users (Double Ratchet state)
        sessions: 'userId, sessionState, lastUpdated',
        
        // Local message cache
        messages: '++id, chatId, sender, recipient, timestamp, encrypted',
        
        // User settings and metadata
        settings: 'key, value'
    });

    // Version 2: Add crypto version tracking
    db.version(2).stores({
        keys: 'id, type, publicKey, privateKey, timestamp',
        sessions: 'userId, sessionState, lastUpdated, version',
        messages: '++id, chatId, sender, recipient, timestamp, encrypted',
        settings: 'key, value'
    }).upgrade(async tx => {
        // Clear all old sessions when upgrading - they use incompatible crypto
        console.log('🔄 Upgrading database: Clearing old sessions (incompatible crypto version)');
        await tx.table('sessions').clear();
    });
    
    // Version 3: Add groups support
    db.version(3).stores({
        keys: 'id, type, publicKey, privateKey, timestamp',
        sessions: 'userId, sessionState, lastUpdated, version',
        messages: '++id, chatId, sender, recipient, timestamp, encrypted',
        settings: 'key, value',
        groups: 'groupId, groupName, groupKey, members, admin, created_at'
    });
    
    // Version 4: Add key history for groups (to decrypt old messages after key rotation)
    db.version(4).stores({
        keys: 'id, type, publicKey, privateKey, timestamp',
        sessions: 'userId, sessionState, lastUpdated, version',
        messages: '++id, chatId, sender, recipient, timestamp, encrypted',
        settings: 'key, value',
        groups: 'groupId, groupName, currentKey, keyHistory, members, admin, created_at'
    }).upgrade(async tx => {
        console.log('🔄 Upgrading database: Adding group key history support');
        // Convert existing groups to new format
        const groups = await tx.table('groups').toArray();
        for (const group of groups) {
            if (group.groupKey && !group.currentKey) {
                // Update to new format
                const updatedGroup = {
                    ...group,
                    currentKey: group.groupKey,
                    keyHistory: [group.groupKey]
                };
                delete updatedGroup.groupKey; // Remove old field
                await tx.table('groups').put(updatedGroup);
                console.log(`✅ Migrated group ${group.groupId} to v4 format`);
            }
        }
    });
    
    return db;
}

/**
 * Store identity key pair
 */
async function storeIdentityKey(publicKey, privateKey) {
    await db.keys.put({
        id: 'identity',
        type: 'identity',
        publicKey: publicKey,
        privateKey: privateKey,
        timestamp: Date.now()
    });
}

/**
 * Get identity key pair
 */
async function getIdentityKey() {
    return await db.keys.get('identity');
}

/**
 * Store signed prekey
 */
async function storeSignedPreKey(keyId, publicKey, privateKey, signature) {
    await db.keys.put({
        id: `signed_prekey_${keyId}`,
        type: 'signed_prekey',
        keyId: keyId,
        publicKey: publicKey,
        privateKey: privateKey,
        signature: signature,
        timestamp: Date.now()
    });
}

/**
 * Get signed prekey
 */
async function getSignedPreKey(keyId) {
    return await db.keys.get(`signed_prekey_${keyId}`);
}

/**
 * Store one-time prekeys
 */
async function storeOneTimePreKeys(prekeys) {
    const promises = prekeys.map(prekey => 
        db.keys.put({
            id: `opk_${prekey.keyId}`,
            type: 'one_time_prekey',
            keyId: prekey.keyId,
            publicKey: prekey.publicKey,
            privateKey: prekey.privateKey,
            timestamp: Date.now()
        })
    );
    await Promise.all(promises);
}

/**
 * Get one-time prekey
 */
async function getOneTimePreKey(keyId) {
    return await db.keys.get(`opk_${keyId}`);
}

/**
 * Store session with another user
 */
async function storeSession(userId, sessionState) {
    await db.sessions.put({
        userId: userId,
        sessionState: sessionState,
        version: 2, // Crypto version: 2 = identity key ECDH
        lastUpdated: Date.now()
    });
}

/**
 * Get session with user
 */
async function getSession(userId) {
    return await db.sessions.get(userId);
}

/**
 * Check if session exists
 */
async function hasSession(userId) {
    const session = await db.sessions.get(userId);
    return !!session;
}

/**
 * Store message locally
 */
async function storeMessage(chatId, sender, recipient, content, encrypted = true) {
    return await db.messages.add({
        chatId: chatId,
        sender: sender,
        recipient: recipient,
        content: content,
        encrypted: encrypted,
        timestamp: Date.now()
    });
}

/**
 * Get messages for a chat
 */
async function getMessages(chatId, limit = 50) {
    return await db.messages
        .where('chatId')
        .equals(chatId)
        .reverse()
        .limit(limit)
        .toArray();
}

/**
 * Clear all data (logout/reset)
 */
async function clearAllData() {
    await db.keys.clear();
    await db.sessions.clear();
    await db.messages.clear();
    await db.settings.clear();
}

/**
 * Get or set setting
 */
async function getSetting(key, defaultValue = null) {
    const setting = await db.settings.get(key);
    return setting ? setting.value : defaultValue;
}

async function setSetting(key, value) {
    await db.settings.put({ key: key, value: value });
}

/**
 * Check and migrate old sessions to new crypto version
 */
async function checkAndMigrateSessions() {
    if (!db) {
        console.warn('Database not initialized, skipping migration check');
        return;
    }
    
    try {
        // Check if we have old sessions without version field
        const allSessions = await db.sessions.toArray();
        let oldSessionsFound = false;
        
        for (const session of allSessions) {
            if (!session.version || session.version < 2) {
                oldSessionsFound = true;
                break;
            }
        }
        
        if (oldSessionsFound) {
            console.log('🔄 Found old sessions with incompatible crypto. Clearing...');
            await db.sessions.clear();
            console.log('✅ Old sessions cleared. New sessions will be created automatically.');
        }
    } catch (error) {
        console.warn('Migration check failed:', error);
    }
}

/**
 * Store group information
 */
async function storeGroup(groupId, groupName, groupKey, members, admin) {
    await db.groups.put({
        groupId: groupId,
        groupName: groupName,
        currentKey: groupKey,  // Current active key
        keyHistory: [groupKey], // Array of all keys (oldest to newest)
        members: members,
        admin: admin,
        created_at: Date.now()
    });
}

/**
 * Get group by ID
 */
async function getGroup(groupId) {
    const group = await db.groups.get(groupId);
    // For backwards compatibility, if old format, convert it
    if (group && group.groupKey && !group.currentKey) {
        group.currentKey = group.groupKey;
        group.keyHistory = [group.groupKey];
    }
    return group;
}

/**
 * Get all groups user is member of
 */
async function getAllGroups() {
    const groups = await db.groups.toArray();
    // Convert old format groups
    for (const group of groups) {
        if (group.groupKey && !group.currentKey) {
            group.currentKey = group.groupKey;
            group.keyHistory = [group.groupKey];
        }
    }
    return groups;
}

/**
 * Update group members
 */
async function updateGroupMembers(groupId, members) {
    const group = await db.groups.get(groupId);
    if (group) {
        group.members = members;
        await db.groups.put(group);
    }
}

/**
 * Update group key (for key rotation)
 * Adds new key to history and sets it as current
 */
async function updateGroupKey(groupId, newGroupKey) {
    const group = await db.groups.get(groupId);
    if (group) {
        // Add new key to history
        if (!group.keyHistory) {
            group.keyHistory = [group.currentKey || group.groupKey];
        }
        group.keyHistory.push(newGroupKey);
        
        // Set as current key
        group.currentKey = newGroupKey;
        
        // Remove old groupKey field if it exists
        delete group.groupKey;
        
        await db.groups.put(group);
    }
}

/**
 * Delete group
 */
async function deleteGroup(groupId) {
    await db.groups.delete(groupId);
}

// Export functions
window.ChatifyDB = {
    get db() { return db; }, // Getter for db
    initDB,
    storeIdentityKey,
    getIdentityKey,
    storeSignedPreKey,
    getSignedPreKey,
    storeOneTimePreKeys,
    getOneTimePreKey,
    storeSession,
    getSession,
    hasSession,
    storeMessage,
    getMessages,
    clearAllData,
    // Group functions
    storeGroup,
    getGroup,
    getAllGroups,
    updateGroupMembers,
    updateGroupKey,
    deleteGroup,
    getSetting,
    setSetting,
    checkAndMigrateSessions
};

console.log('📦 IndexedDB module loaded (awaiting initialization)');

console.log('📦 IndexedDB initialized');
