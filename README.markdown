# PeerPulse: Decentralized Chat Application with Blockchain

A peer-to-peer chat application for secure team communication, enhanced with blockchain for immutable message storage, built with Flask, Flask-SocketIO, and HTML/CSS/JavaScript.

## Features
- P2P messaging with dynamic peer discovery via `peers.json`.
- Blockchain-based message and file storage with proof-of-work consensus.
- AES-encrypted messages and file sharing (images/text, max 1MB).
- User authentication with persistent IDs.
- Real-time message broadcasting with latency metrics.
- Cross-device support on the same network (via `0.0.0.0` binding).

## Setup
1. Clone the repository or copy files to `E:\DecentralizedChat`.
2. Create a virtual environment: `python -m venv .venv`.
3. Activate: `E:\DecentralizedChat\.venv\Scripts\activate`.
4. Install dependencies: `pip install flask flask-socketio python-socketio jsonpickle`.
5. Create `peers.json` (e.g., `[5001]`) for P2P.
6. Run server: `python app.py 5000`.
7. Access: `http://<server-ip>:5000/?port=5000` (e.g., `http://192.168.1.100:5000`).

## Testing
- **Single Server**: Run `python app.py 5000`, open multiple tabs/devices on `http://<server-ip>:5000/?port=5000`.
- **P2P**: Run `python app.py 5000` and `python app.py 5001`, test cross-port messaging and blockchain sync.
- Check `blockchain_<port>.json` for stored messages and files.
- Verify logs for latency and blockchain mining.

## Future Improvements
- End-to-end encryption with user-specific keys.
- Offline message queuing with blockchain persistence.
- Scalable peer discovery via UDP broadcasting.