# Chatify - Secure Decentralized Chat

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

A secure, real-time chat application with **end-to-end encryption** using the Signal Protocol (libsignal).

## 🎓 Project Type
**Final Year College Project** - Computer Science/Engineering  
**Academic Year:** 2025-2026

## ✨ Features

### Core Features
- 🔐 **End-to-End Encryption** using Signal Protocol (X3DH + Double Ratchet)
- 💬 **Private Chat** - Secure 1-to-1 messaging
- 👥 **Group Chat** - Multi-user encrypted conversations
- 📁 **File Sharing** - Share encrypted files, images, videos (up to 16MB)
- 🎤 **Voice Messages** - Record and send audio messages
- 📱 **Device Linking** - QR-based secure multi-device support
- 🌐 **Server-Wide Chat** - Public chat room

### UX Features
- ⌨️ Typing indicators
- ✅ Read receipts (sent/delivered/read)
- 🟢 Online/offline status
- 😊 Message reactions
- ✏️ Edit/delete messages
- 🌙 Dark/light mode
- 📱 Responsive design (mobile-friendly)
- 😀 Emoji picker (200+ emojis)
- 🎬 GIF picker (GIPHY integration)
- 🔗 Rich text formatting (markdown)

## 🏗️ Architecture

```
┌─────────────┐      Encrypted      ┌──────────────┐      Key Exchange      ┌─────────────┐
│  Client A   │ ◄──────Messages─────►│    Server    │◄────& Message Relay───►│  Client B   │
│ (libsignal) │      (ciphertext)    │ Flask+Socket │     (public keys)      │ (libsignal) │
└─────────────┘                      └──────────────┘                        └─────────────┘
      │                                      │
      │                                      ▼
      ▼                               ┌──────────────┐
┌─────────────┐                       │   MongoDB    │
│  IndexedDB  │                       │   - Users    │
│ (private    │                       │   - Messages │
│  keys)      │                       │   - Groups   │
└─────────────┘                       └──────────────┘
```

## 🛠️ Tech Stack

**Backend:**
- Flask (Python web framework)
- Flask-SocketIO (WebSocket support)
- MongoDB (Database)
- libsignal (Signal Protocol implementation)
- bcrypt (Password hashing)

**Frontend:**
- HTML5, CSS3, JavaScript (ES6+)
- TailwindCSS (Styling)
- @signalapp/libsignal-client (E2E encryption)
- Socket.IO client (Real-time communication)
- Dexie.js (IndexedDB for key storage)

## 📋 Prerequisites

- Python 3.9 or higher
- MongoDB 6.0+ (local or Atlas)
- Modern web browser (Chrome, Firefox, Edge)
- Git

## 🚀 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/chatify.git
cd chatify
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory:
```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/chatify
# Or use MongoDB Atlas:
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/chatify

# Server Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=True

# File Upload
MAX_FILE_SIZE=16777216  # 16MB in bytes
UPLOAD_FOLDER=uploads
```

### 5. Setup MongoDB
- **Option A (Local):** Install MongoDB Community Edition
- **Option B (Cloud):** Create free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

### 6. Setup GIPHY API (Optional - for GIF picker)
To enable the GIF picker feature:
1. Go to [GIPHY Developers](https://developers.giphy.com/)
2. Create a free account
3. Create a new app (choose "SDK" type)
4. Copy your API key
5. Open `templates/chat.html` and replace `YOUR_GIPHY_API_KEY_HERE` with your actual API key

**Note:** The app works without this - GIF picker just won't load GIFs until configured.

### 7. Run the application
```bash
python app.py
```

The application will be available at: `http://localhost:5000`

## 📁 Project Structure

```
chatify/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create this)
├── .gitignore                 # Git ignore rules
│
├── app/
│   ├── __init__.py            # App initialization
│   ├── models.py              # Database models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication routes
│   │   ├── chat.py            # Chat routes
│   │   ├── keys.py            # Key management routes
│   │   └── files.py           # File upload/download routes
│   │
│   ├── socket_events.py       # Socket.IO event handlers
│   └── utils/
│       ├── __init__.py
│       ├── database.py        # Database utilities
│       └── security.py        # Security utilities
│
├── static/
│   ├── css/
│   │   └── style.css          # Custom styles
│   ├── js/
│   │   ├── app.js             # Main JavaScript
│   │   ├── crypto.js          # libsignal wrapper
│   │   ├── socket.js          # Socket.IO client
│   │   ├── ui.js              # UI management
│   │   └── storage.js         # IndexedDB management
│   └── assets/
│       └── images/
│
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Landing page
│   ├── register.html          # Registration page
│   ├── login.html             # Login page
│   └── chat.html              # Main chat interface
│
├── uploads/                    # File uploads directory
│   └── .gitkeep
│
├── tests/                      # Test files
│   ├── test_auth.py
│   ├── test_crypto.py
│   └── test_socket.py
│
└── docs/
    ├── API.md                 # API documentation
    ├── ARCHITECTURE.md        # Architecture details
    └── SECURITY.md            # Security analysis
```

## 🔐 Security Features

- **Signal Protocol** (X3DH + Double Ratchet)
- **Forward Secrecy** - Each message uses unique keys
- **Post-Compromise Security** - Future messages remain secure after key compromise
- **Zero Knowledge Server** - Server never sees plaintext messages
- **bcrypt Password Hashing** - Secure credential storage
- **TLS/SSL** - All transport encrypted (HTTPS/WSS)
- **File Integrity Verification** - SHA-256 checksums

## 📊 Development Status

- [x] Phase 0: Project Setup ✅
- [ ] Phase 1: Authentication
- [ ] Phase 2: libsignal Integration
- [ ] Phase 3: Private Chat
- [ ] Phase 4: Real-Time Features
- [ ] Phase 5: Group Chat
- [ ] Phase 6: File Sharing
- [ ] Phase 7: Message Enhancements
- [ ] Phase 8: Device Linking
- [ ] Phase 9: UI Polish
- [ ] Phase 10: Testing & Documentation

See `plan.md` for detailed roadmap.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

## 📚 Documentation

- [Development Plan](plan.md) - Detailed project roadmap
- [API Documentation](docs/API.md) - REST and Socket.IO API reference
- [Architecture Guide](docs/ARCHITECTURE.md) - System design and components
- [Security Analysis](docs/SECURITY.md) - Threat model and countermeasures

## 🎯 Learning Outcomes

This project demonstrates:
- ✅ Full-stack web development
- ✅ Real-time communication systems
- ✅ Applied cryptography (Signal Protocol)
- ✅ Database design (MongoDB)
- ✅ Security best practices
- ✅ Modern software architecture

## 🤝 Contributing

This is an academic project. If you'd like to suggest improvements:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

**Your Name**  
Final Year Project - Computer Science/Engineering  
University Name - 2025-2026

## 🙏 Acknowledgments

- Signal Protocol - Open Whisper Systems
- Flask & Socket.IO communities
- MongoDB documentation
- My project supervisor and peers

## 📞 Contact

For questions or demo requests:
- Email: your.email@example.com
- LinkedIn: [Your Profile]
- GitHub: [@yourusername]

---

**Built with ❤️ for secure communication**
