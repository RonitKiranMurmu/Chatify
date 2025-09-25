# 🔒 Secure Enviro# Security (Generate your own random)
SECRET_KEY=your-super-long-random-secret-key-here

# Encryption Secret (Generate unique secret)
ENCRYPTION_SECRET=your-unique-encryption-secret-here

# Environment Detection
RENDER=true

# External URL (Render sets automatically)
RENDER_EXTERNAL_URL=https://your-app-name.onrender.com Setup for Render

## ⚠️ SECURITY NOTICE
**NEVER commit real credentials to Git!** Always set sensitive values in the Render dashboard.

## 🚀 Render Deployment Setup

### 1. Environment Variables (Set in Render Dashboard)

Go to your Render service → Environment tab and add:

```bash
# MongoDB Atlas (Required)
MONGO_URI=mongodb+srv://your_username:your_password@your_cluster.mongodb.net/your_database

# Database Name
MONGO_DB=chatify

# Security (Generate random)
SECRET_KEY=your-super-long-random-secret-key-here

# Environment Detection
RENDER=true
```

### 2. Generate Secure Keys

Use Python to generate secure keys:

```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### 3. MongoDB Atlas Setup

1. Create MongoDB Atlas account
2. Create cluster
3. Add database user
4. Whitelist Render IP ranges (0.0.0.0/0 for simplicity)
5. Get connection string

### 4. Render Configuration

**Build Command:** `pip install -r requirements.txt`
**Start Command:** `gunicorn --worker-class gevent --workers 1 --bind 0.0.0.0:$PORT app:app`

## 🛡️ Security Best Practices

- ✅ All credentials set in Render dashboard (not in code)
- ✅ Environment files in .gitignore
- ✅ MongoDB Atlas with authentication
- ✅ TLS encryption for database connections
- ✅ Encrypted message storage

## 📞 Support

If you need help with secure deployment, check the Render documentation or MongoDB Atlas guides.