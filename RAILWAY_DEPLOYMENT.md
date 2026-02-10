# Railway.app Deployment Guide

## Quick Start (5 minutes)

Railway is the easiest way to deploy your RestlessResume app to the cloud. Follow these steps:

### **Step 1: Push Code to GitHub (If Not Already Done)**

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/RestlessResume.git
git push -u origin main
```

### **Step 2: Create Railway Account**

1. Go to **https://railway.app**
2. Click "Start Project"
3. Sign up with GitHub (recommended - easier integration)
4. Authorize Railway to access your GitHub

### **Step 3: Create New Project**

1. Click "New Project"
2. Select "Deploy from GitHub"
3. Choose your RestlessResume repository
4. Click "Deploy"

Railway will automatically:
- ✅ Detect your Dockerfile
- ✅ Build the Docker image
- ✅ Provision a PostgreSQL database
- ✅ Deploy your app

### **Step 4: Configure Environment Variables**

In Railway dashboard, go to your project → Variables tab → Add these:

```
OPENAI_API_KEY=sk-xxxxx...          # Your OpenAI API key
GOOGLE_CLIENT_ID=xxxxx.apps.xxx     # From Google Cloud Console
GOOGLE_CLIENT_SECRET=xxxxx          # From Google Cloud Console
SESSION_SECRET_KEY=<random-string>  # Generate: python -c "import secrets; print(secrets.token_hex(32))"
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Note:** Railway automatically creates `DATABASE_URL` from the PostgreSQL plugin.

### **Step 5: Add PostgreSQL Database**

1. In Railway project, click "+ Add"
2. Select "Database" → "PostgreSQL"
3. Choose PostgreSQL 16
4. Railway automatically sets `DATABASE_URL` environment variable
5. Database is ready!

### **Step 6: Deploy**

1. Keep "Auto-deploy from GitHub" **enabled** (default)
2. Every push to `main` branch = automatic deployment
3. Check deployment status in Railway dashboard

### **Step 7: Access Your App**

1. Go to Railway project → Deployments
2. Click your deployment → "View Logs"
3. Once deployment shows ✅, app is live!
4. Click "Visit" or find your domain: `yourproject.railway.app`

---

## **Environment Variables Setup**

### **Generate SESSION_SECRET_KEY**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This produces a secure random string like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### **Get OpenAI API Key**

1. Go to **https://platform.openai.com/api-keys**
2. Create new API key
3. Copy and paste into Railway variables

### **Get Google OAuth Credentials**

1. Go to **https://console.cloud.google.com**
2. Create new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URIs:
   - `http://localhost:8000/auth/callback` (local testing)
   - `https://yourproject.railway.app/auth/callback` (production)
6. Copy Client ID and Secret to Railway

---

## **Verify Deployment**

Once deployed, you should see:

1. ✅ PostgreSQL database running
2. ✅ App container running
3. ✅ Health check passing
4. ✅ Logs showing "Application startup complete"

### **Check App Health**

```bash
curl https://yourproject.railway.app/health
# Should return: {"status": "healthy"}
```

### **View Logs**

In Railway dashboard → Deployments → Logs tab

---

## **GitHub Actions CI/CD (Optional)**

The `.github/workflows/deploy-railway.yml` file enables:

1. ✅ Auto builds Docker image on every push
2. ✅ Pushes to Docker Hub (optional, for backup)
3. ✅ Auto-deploys to Railway on main branch push

### **To Enable CI/CD:**

1. Create Docker Hub account: https://hub.docker.com
2. Add GitHub Secrets:
   - `DOCKER_USERNAME` → Your Docker Hub username
   - `DOCKER_PASSWORD` → Your Docker Hub access token
   - `RAILWAY_TOKEN` → Get from Railway dashboard
   - `RAILWAY_SERVICE_ID` → Your Railway service ID

3. Push to GitHub:
   ```bash
   git add .github/workflows/deploy-railway.yml
   git commit -m "Add GitHub Actions CI/CD"
   git push origin main
   ```

---

## **Local Testing Before Cloud Deployment**

Test Docker image locally:

```bash
# Build image
docker build -t test-resume .

# Run with environment
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e GOOGLE_CLIENT_ID=your-id \
  -e GOOGLE_CLIENT_SECRET=your-secret \
  -e SESSION_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  test-resume

# Visit http://localhost:8000 in browser
```

---

## **Troubleshooting**

### **Deployment Stuck**

1. Check Railway dashboard → Logs
2. Look for error messages
3. Common issues:
   - Missing environment variables
   - Database not ready
   - Port already in use

### **App Crashes**

Check logs for:
- `ModuleNotFoundError` → Dependencies missing
- `DatabaseError` → PostgreSQL not ready
- `KeyError` → Missing environment variable

**Solution:** View logs in Railway dashboard, fix issue locally, push to GitHub, Railway auto-redeploys.

### **Database Connection Error**

```
ERROR: could not connect to server: Connection refused
```

**Solution:**
1. Verify PostgreSQL plugin is added to Railway
2. Check DATABASE_URL environment variable is set
3. Wait 30 seconds for database to initialize

---

## **Scaling & Monitoring**

Once deployed, Railway makes it easy to:

- **Scale:** Increase CPU/RAM in Railway dashboard
- **Monitor:** View metrics, logs, deployment history
- **Backups:** Railway PostgreSQL auto-backs up daily
- **Custom Domain:** Point your domain to Railway app
- **SSL/TLS:** Auto-provided by Railway

---

## **Next Steps**

1. ✅ Push code to GitHub
2. ✅ Create Railway project
3. ✅ Add PostgreSQL
4. ✅ Set environment variables
5. ✅ Deploy!
6. ✅ Share URL with others: `https://yourproject.railway.app`

Your app is now **live on the internet** for anyone to access! 🚀

---

## **Support**

- Railway Docs: https://docs.railway.app
- Railway Discord: https://railway.app/support
- GitHub Issues: https://github.com/railwayapp/railway.app/issues
