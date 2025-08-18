# Project Synopsis: PeerPulse - A Decentralized Chat Application with Blockchain

## Title
PeerPulse: A Decentralized Chat Application with Blockchain for Secure Team Communication

## Objective
To develop a peer-to-peer (P2P) chat application with blockchain-based message storage, enabling secure, real-time, and tamper-proof communication across devices on a local network without central servers, suitable for small team collaboration.

## Introduction
PeerPulse integrates Flask, Flask-SocketIO, and a custom blockchain to provide a decentralized chat system for secure team communication. It supports P2P messaging, AES encryption, file sharing, user authentication, and immutable message storage via a proof-of-work blockchain, making it an innovative solution for Computer Networks (CN312) coursework.

## Methodology
- **Backend**: Flask with Flask-SocketIO, binding to `0.0.0.0` for cross-device access, using WebSocket for real-time communication and a custom blockchain for message storage.
- **Blockchain**: Implements proof-of-work consensus, storing messages and files as transactions in `blockchain_<port>.json`, synchronized across P2P nodes.
- **Frontend**: HTML/CSS/JavaScript with Socket.IO client for user interface, AES encryption, and blockchain transaction display.
- **Features**: P2P message forwarding, AES-encrypted messages/files, user authentication, file sharing (1MB limit), dynamic peer discovery, and latency metrics.
- **Testing**: Deployed on multiple ports (e.g., 5000, 5001) with peer discovery via `peers.json`, tested for message consistency and blockchain synchronization across devices.

## Real-Use Case
Secure, decentralized communication for small teams (2–3 users) in environments requiring privacy and verifiable message history, such as academic or small-scale professional settings.

## Tools and Technologies
- Python 3.13, Flask, Flask-SocketIO, python-socketio, jsonpickle
- HTML, CSS, JavaScript, Socket.IO, CryptoJS
- Visual Studio Code, Windows environment

## Future Scope
- Implement end-to-end encryption with user-specific keys.
- Add offline message storage and delivery via blockchain.
- Enhance peer discovery with UDP-based broadcasting for scalability.