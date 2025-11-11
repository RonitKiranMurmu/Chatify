# 🔧 Gevent vs Eventlet on Render

## ⚠️ Important: Use Gevent (Not Eventlet)

### Why Gevent?

Based on real-world Render deployments, **gevent** is more reliable than eventlet:

1. **Better Compatibility**: Gevent works consistently on Render's infrastructure
2. **Fewer Edge Cases**: Less likely to have connection timeout issues
3. **Proven Track Record**: More production deployments use gevent on Render
4. **Active Maintenance**: Better support for modern Python versions

---

## ✅ Configuration Changes

### Procfile
```bash
# ❌ OLD (Don't use)
web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app

# ✅ NEW (Use this)
web: gunicorn --worker-class gevent -w 1 --bind 0.0.0.0:$PORT app:app
```

### requirements.txt
```txt
# ❌ OLD (Don't use)
eventlet==0.33.3

# ✅ NEW (Use this)
gevent==23.9.1
gevent-websocket==0.10.1
```

### config.py
```python
# ✅ Update async mode
SOCKETIO_ASYNC_MODE = 'gevent'  # Changed from 'threading'
```

---

## 🧪 Testing Locally with Gevent

### Install Gevent
```powershell
pip install gevent gevent-websocket
```

### Run with Gunicorn (Production Mode)
```powershell
gunicorn --worker-class gevent -w 1 --bind 127.0.0.1:5000 app:app
```

### Test WebSocket Connection
1. Open browser: `http://127.0.0.1:5000`
2. Register and login
3. Send messages
4. Check console for errors

---

## 🔍 Troubleshooting

### Issue: "gevent not found"
```powershell
pip install gevent gevent-websocket
```

### Issue: WebSocket not connecting
**Check config.py**:
```python
SOCKETIO_ASYNC_MODE = 'gevent'  # Must match worker class
```

### Issue: Import errors
**Check you removed eventlet**:
```powershell
pip uninstall eventlet
pip install -r requirements.txt
```

---

## 📊 Performance Comparison

### Gevent on Render
- ✅ Reliable WebSocket connections
- ✅ Low memory overhead
- ✅ Good concurrency handling
- ✅ Fast cold starts

### Eventlet on Render
- ⚠️ Occasional connection timeouts
- ⚠️ More finicky configuration
- ⚠️ Less predictable behavior

---

## 🎯 Deployment Command

**Always use this on Render:**
```bash
gunicorn --worker-class gevent -w 1 --bind 0.0.0.0:$PORT app:app
```

**Key Parameters:**
- `--worker-class gevent`: Async worker for WebSocket
- `-w 1`: Single worker (required for Socket.IO state)
- `--bind 0.0.0.0:$PORT`: Listen on all interfaces, Render's port
- `app:app`: Your Flask app instance

---

## ✨ Already Updated Files

All deployment files have been updated to use gevent:

- ✅ `Procfile`
- ✅ `render.yaml`
- ✅ `requirements.txt`
- ✅ `config.py`
- ✅ `RENDER_DEPLOYMENT.md`
- ✅ `DEPLOYMENT_CHECKLIST.md`
- ✅ `QUICK_DEPLOY.md`
- ✅ `DEPLOYMENT_SUMMARY.md`

**You're ready to deploy with gevent!** 🚀
