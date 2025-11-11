# 🚀 Render Deployment Checklist

## Pre-Deployment

- [ ] All code committed to Git
- [ ] `.env` file is in `.gitignore` (DO NOT COMMIT)
- [ ] MongoDB Atlas connection tested
- [ ] `requirements.txt` includes `gunicorn`
- [ ] Files created:
  - [ ] `Procfile`
  - [ ] `render.yaml`
  - [ ] `.python-version`
  - [ ] `RENDER_DEPLOYMENT.md`

## Render Setup

- [ ] Create Render account at https://render.com
- [ ] Push code to GitHub/GitLab
- [ ] Create new Web Service on Render
- [ ] Connect to repository
- [ ] Select branch: `optimized`

## Configuration

- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `gunicorn --worker-class gevent -w 1 --bind 0.0.0.0:$PORT app:app`
- [ ] **Environment**: Python 3
- [ ] **Instance Type**: Free (or Starter)

## Environment Variables

Add these in Render dashboard:

- [ ] `FLASK_ENV` = `production`
- [ ] `SECRET_KEY` = (Generate using Render's "Generate" button)
- [ ] `DEBUG` = `False`
- [ ] `HOST` = `0.0.0.0`
- [ ] `MONGODB_URI` = Your MongoDB Atlas connection string
- [ ] `MAX_FILE_SIZE` = `16777216`
- [ ] `UPLOAD_FOLDER` = `/tmp/uploads`
- [ ] `ALLOWED_EXTENSIONS` = `jpg,jpeg,png,gif,pdf,doc,docx,txt,mp4,mp3,wav,ogg,webm`
- [ ] `SESSION_TYPE` = `filesystem`
- [ ] `PERMANENT_SESSION_LIFETIME` = `86400`
- [ ] `BCRYPT_LOG_ROUNDS` = `12`
- [ ] `CORS_ORIGINS` = `*` (update after deployment)
- [ ] `RENDER` = `true`

## MongoDB Atlas Security

- [ ] Go to MongoDB Atlas → Network Access
- [ ] Add IP Address: `0.0.0.0/0` (allow all)
- [ ] Verify database user credentials
- [ ] Test connection from Render

## Deploy

- [ ] Click "Create Web Service"
- [ ] Wait 3-5 minutes for build
- [ ] Check logs for "Server starting..." message
- [ ] Note your Render URL: `https://chatify-xxxx.onrender.com`

## Post-Deployment Testing

- [ ] Visit Render URL
- [ ] Register a new test user
- [ ] Check MongoDB Atlas - user created?
- [ ] Open two browser windows
- [ ] Register two users
- [ ] Test real-time chat
- [ ] Verify WebSocket connection
- [ ] Check message encryption in MongoDB (should see ciphertext only)

## Security Updates

- [ ] Update `CORS_ORIGINS` to your Render URL
- [ ] Verify SSL certificate (should be automatic)
- [ ] Test HTTPS and WSS (secure WebSocket)

## Optional Enhancements

- [ ] Add custom domain
- [ ] Set up monitoring/alerts
- [ ] Configure auto-deploy on git push
- [ ] Add health check endpoint (already exists: `/health`)

## Documentation

- [ ] Update README.md with live demo link
- [ ] Add deployment badge to GitHub
- [ ] Document any issues encountered
- [ ] Share with team/professor

## Troubleshooting

If deployment fails:

1. **Check Render Logs** for specific error
2. **Common Issues**:
   - Missing dependencies → Check `requirements.txt`
   - Port binding error → Verify `HOST=0.0.0.0`
   - MongoDB connection → Check Atlas IP whitelist
   - WebSocket fails → Ensure `gevent` worker used (not eventlet)

3. **Review**: `RENDER_DEPLOYMENT.md` for detailed solutions

---

## ✅ Success Indicators

- ✅ Build completes without errors
- ✅ Logs show "Server starting..."
- ✅ Website loads at Render URL
- ✅ Users can register/login
- ✅ Real-time messages work
- ✅ MongoDB stores encrypted messages

---

**Ready to deploy? Let's go! 🚀**

Start here: https://dashboard.render.com/
