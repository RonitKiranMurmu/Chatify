# Chatify Setup Instructions

## Phase 0: Project Setup (COMPLETED ✅)

Congratulations! The project structure has been created successfully.

## Current Status

```
✅ Project structure created
✅ Configuration files set up
✅ Flask application skeleton ready
✅ Database models defined
✅ Authentication routes implemented
✅ Socket.IO event handlers created
✅ Frontend templates created (basic UI)
✅ CSS styling added
```

## Next Steps

### 1. Install Python Dependencies

Open PowerShell in the project directory and run:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup MongoDB

**Option A: Local MongoDB**
- Download and install MongoDB Community Edition from: https://www.mongodb.com/try/download/community
- Start MongoDB service:
  ```powershell
  net start MongoDB
  ```

**Option B: MongoDB Atlas (Cloud - Recommended for beginners)**
1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free account
3. Create a free cluster (M0)
4. Get connection string
5. Update `.env` file with your connection string:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/chatify?retryWrites=true&w=majority
   ```

### 3. Test the Application

```powershell
# Make sure virtual environment is activated
python app.py
```

You should see:
```
╔═══════════════════════════════════════════╗
║         Chatify - Secure Chat App         ║
║     End-to-End Encrypted Messaging        ║
╚═══════════════════════════════════════════╝

🚀 Server starting...
📍 URL: http://0.0.0.0:5000
```

### 4. Test in Browser

Open your browser and go to: http://localhost:5000

You should see the Chatify homepage!

## Testing Registration and Login

1. Click "Sign Up" to register
2. Create a test account:
   - Username: `alice`
   - Password: `password123`
3. After registration, you'll be redirected to the chat interface
4. Open another browser (or incognito window) and create another user:
   - Username: `bob`
   - Password: `password123`

**Note:** In Phase 0, the encryption keys are placeholder values. We'll implement real libsignal encryption in Phase 2.

## Project Structure

```
chatify/
├── app.py                  # Main application entry point ✅
├── config.py              # Configuration settings ✅
├── requirements.txt       # Python dependencies ✅
├── .env                   # Environment variables ✅
├── plan.md               # Project roadmap ✅
├── README.md             # Project documentation ✅
│
├── app/                   # Application package
│   ├── __init__.py       # App factory ✅
│   ├── models.py         # Database models ✅
│   ├── socket_events.py  # Socket.IO handlers ✅
│   ├── routes/           # Route blueprints
│   │   ├── auth.py       # Authentication ✅
│   │   ├── chat.py       # Chat routes ✅
│   │   ├── keys.py       # Key management ✅
│   │   └── files.py      # File upload/download ✅
│   └── utils/            # Utility modules
│       ├── database.py   # MongoDB utilities ✅
│       └── security.py   # Security functions ✅
│
├── static/               # Static files
│   ├── css/
│   │   └── style.css    # Custom styles ✅
│   └── js/              # JavaScript (Phase 2+)
│
├── templates/            # HTML templates
│   ├── base.html        # Base template ✅
│   ├── index.html       # Landing page ✅
│   ├── register.html    # Registration ✅
│   ├── login.html       # Login ✅
│   └── chat.html        # Chat interface ✅
│
└── uploads/             # File uploads directory ✅
```

## What Works Now (Phase 0)

✅ **Backend:**
- Flask server with Socket.IO
- MongoDB connection
- User registration and login
- Session management
- Basic authentication
- Database models ready

✅ **Frontend:**
- Responsive UI with Tailwind CSS
- Landing page
- Registration form
- Login form
- Basic chat interface
- Contact list (loads users)

## What's Next (Phase 1)

🔄 **To Implement:**
- Improve UI/UX
- Add form validation improvements
- Better error handling
- Session persistence
- User profile pages
- Password reset functionality

## Troubleshooting

### MongoDB Connection Error
- **Local:** Make sure MongoDB service is running
- **Atlas:** Check connection string and network access settings

### Module Import Errors
```powershell
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Port Already in Use
Change the PORT in `.env` file:
```
PORT=5001
```

### Socket.IO Connection Issues
- Make sure eventlet is installed: `pip install eventlet`
- Check browser console for errors

## Development Workflow

1. **Start MongoDB** (if local)
2. **Activate virtual environment**: `.\venv\Scripts\Activate.ps1`
3. **Run the app**: `python app.py`
4. **Open browser**: http://localhost:5000
5. **Make changes** to code
6. **Server auto-reloads** (in DEBUG mode)

## Git Commands

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Phase 0: Initial project setup"

# Add remote (create repo on GitHub first)
git remote add origin https://github.com/yourusername/chatify.git

# Push
git push -u origin main
```

## Phase Checklist

- [x] **Phase 0: Project Setup** ✅ COMPLETED
  - [x] Project structure
  - [x] Flask + Socket.IO + MongoDB
  - [x] Basic authentication
  - [x] Frontend UI templates
  - [x] Configuration files

- [ ] **Phase 1: Authentication Enhancement** (Next)
  - [ ] Improve validation
  - [ ] Better error handling
  - [ ] User profile functionality

- [ ] **Phase 2: libsignal Integration** (Upcoming)
  - [ ] Install libsignal library
  - [ ] Generate real encryption keys
  - [ ] Implement key exchange

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Socket.IO Documentation](https://socket.io/docs/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Signal Protocol](https://signal.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)

## Need Help?

Check the following:
1. Make sure all dependencies are installed
2. MongoDB is running and accessible
3. `.env` file is configured correctly
4. Port 5000 is not in use

---

**🎉 Congratulations on completing Phase 0!**

Ready to move to Phase 1? Run the app and test it out first!
