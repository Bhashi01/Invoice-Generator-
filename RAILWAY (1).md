# Railway Deployment Guide (Docker Version)

For deploying the **full React + FastAPI** version to Railway with custom domain.

## 🚂 Quick Start

### 1. Push to GitHub

```bash
cd trainer-invoice-app  # The Docker version with backend/frontend
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/trainer-invoice-app.git
git push -u origin main
```

### 2. Deploy to Railway

1. Go to https://railway.app
2. Sign in with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose `trainer-invoice-app`
6. Railway auto-detects docker-compose.yml

### 3. Configure Services

Railway creates 2 services automatically:
- `backend` (port 8000)
- `frontend` (port 80)

**For frontend:**
1. Click on frontend service
2. Settings → Networking → **"Generate Domain"**
3. You get: `https://yourapp.railway.app`

**For backend (if needed separately):**
1. Click backend service  
2. Settings → Networking → **"Generate Domain"**
3. Update frontend to point to this domain

### 4. Set Environment Variables

Click `backend` → **"Variables"** tab:

```
DB_PATH=/app/data/invoices.db
BILLED_TO_NAME=Metis Eduventures Private Limited
BILLED_TO_ADDRESS=2nd floor, 207A-208, Tower A, Unitech Cyber Park, Sec-39 Gurgaon, Haryana - 122001
BILLED_TO_GSTIN=06AAHCM7263M1ZZ
```

### 5. Persistent Storage

Railway provides ephemeral storage by default. For persistent DB:

1. Click backend → **"Volumes"**
2. Add volume:
   - Mount path: `/app/data`
3. This ensures database persists across deploys

Add another volume for PDFs:
   - Mount path: `/app/invoices_out`

### 6. Custom Domain (Optional)

1. Buy domain from Namecheap, GoDaddy, etc.
2. In Railway: Settings → Networking → **"Custom Domain"**
3. Add your domain: `invoices.yourcompany.com`
4. Update your DNS:
   - Type: `CNAME`
   - Name: `invoices` (or `@` for root)
   - Value: (Railway provides this)
5. Wait 5-30 minutes for DNS propagation

### 7. Auto-Deploy

Every time you push to GitHub:
```bash
git add .
git commit -m "Updated feature"
git push
```

Railway automatically rebuilds and deploys (2-3 min).

## 💰 Pricing

- **Free Trial:** $5 credit
- **After trial:** ~$5-10/month
  - Backend: ~$3/month
  - Frontend: ~$2/month
  - Database storage: ~$1/month

**Much cheaper than:**
- Heroku: $14/month
- DigitalOcean: $12/month minimum
- AWS: Variable, usually $15+/month

## 🔧 Advanced Configuration

### Add Authentication

Install `streamlit-authenticator`:

```bash
pip install streamlit-authenticator
```

Or for React version, add Auth0 / Clerk.

### Database Backups

Railway doesn't auto-backup SQLite. Options:

**Option 1: Manual**
```bash
railway run bash
cd data
cp invoices.db invoices.db.backup
```

**Option 2: Automated (cron)**
Add to backend:
```python
import schedule
import shutil

def backup_db():
    shutil.copy('data/invoices.db', f'data/backup_{datetime.now():%Y%m%d}.db')

schedule.every().day.at("02:00").do(backup_db)
```

**Option 3: Use PostgreSQL**
Railway offers PostgreSQL for free:
1. Add PostgreSQL plugin in Railway
2. Update code to use Postgres instead of SQLite
3. Railway auto-backs up Postgres

### Monitoring

Railway dashboard shows:
- CPU usage
- Memory usage  
- Request logs
- Build logs
- Crash reports

### Logs

View live logs:
```bash
railway logs
```

Or in Railway dashboard: Service → **"Deployments"** → **"View Logs"**

## 🆚 Streamlit vs Railway

| Feature | Streamlit Cloud | Railway |
|---------|----------------|---------|
| **Best for** | Internal teams | Production apps |
| **Setup** | 5 minutes | 10 minutes |
| **Cost** | FREE | $5-10/month |
| **UI** | Streamlit only | Any (React, Vue, etc) |
| **Users** | 50-100 | Unlimited |
| **Custom Domain** | ❌ No | ✅ Yes |
| **Database** | SQLite on their server | Your choice |
| **Control** | Limited | Full control |

## 🎯 Recommendation

**Use Streamlit Cloud if:**
- Internal team tool (5-50 people)
- Don't need custom domain
- Want FREE hosting
- Want simplest deployment

**Use Railway if:**
- Customer-facing product
- Need custom domain
- Need 100+ concurrent users
- Want full React frontend
- Need database backups
- Willing to pay $5-10/month

## 🔗 Useful Links

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Railway Status: https://status.railway.app

---

**Pro tip:** Start with Streamlit (free), then migrate to Railway when you outgrow it. Your database and invoice_generator.py will work on both! 🚀
