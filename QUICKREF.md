# hero-evidence-library Quick Reference

## 🚀 Common Operations

### Deploy/Redeploy
```bash
# From dev machine
./deploy.sh
```

### Check Status
```bash
# On mac-mini
ssh mac-mini
lsof -i:8400  # Backend
lsof -i:3400  # Frontend
pg_isready    # Database
mount | grep dev-pdfs  # PDF mount
```

### View Logs
```bash
# On mac-mini
tail -f ~/production/hero-evidence-library/hero_evidence_library_backend.log
tail -f ~/production/hero-evidence-library/hero_evidence_library_frontend.log
tail -f /tmp/cloudflared.log
```

### Restart Services
```bash
# On mac-mini
cd ~/production/hero-evidence-library

# Backend
pkill -f "uvicorn.*8400"
cd backend && source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8400 > ../hero_evidence_library_backend.log 2>&1 &

# Frontend
pkill -f "next.*3400"
cd frontend/nextjs-app
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 22
nohup npm run start -- -p 3400 > ../../hero_evidence_library_frontend.log 2>&1 &
```

### Remount PDFs
```bash
# On mac-mini
umount /tmp/dev-pdfs
cd ~/production/hero-evidence-library
./scripts/setup-pdf-mount.sh
```

### Database Operations
```bash
# On mac-mini
# Reset database
./scripts/init-production-db.sh

# Backup database
pg_dump -U postgres hero_evidence_library_prod | gzip > ~/backups/backup_$(date +%Y%m%d).sql.gz

# Connect to database
psql -U postgres -d hero_evidence_library_prod
```

## 🌐 URLs

- **Public**: https://library.counterforce-hero.tech
- **Backend** (local): http://localhost:8400
- **Frontend** (local): http://localhost:3400
- **API Docs**: http://localhost:8400/docs

## 📁 Important Paths

### Dev Machine
- Project: `~/dev/hero-counterforce/hero_evidence_library`
- PDFs: `~/dev/hero-counterforce/hero_evidence_library/backend/data/pdfs`

### Production (mac-mini)
- Project: `~/production/hero-evidence-library`
- Backend: `~/production/hero-evidence-library/backend`
- Frontend: `~/production/hero-evidence-library/frontend/nextjs-app`
- PDFs (mounted): `/tmp/dev-pdfs`
- Logs: `~/production/hero-evidence-library/*.log`

## 🔧 Troubleshooting Quick Fixes

### Backend won't start
```bash
cd ~/production/hero-evidence-library/backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't start
```bash
cd ~/production/hero-evidence-library/frontend/nextjs-app
nvm use 22
npm install
npm run build
```

### PDF mount lost
```bash
umount /tmp/dev-pdfs 2>/dev/null
./scripts/setup-pdf-mount.sh
```

### Database connection failed
```bash
brew services restart postgresql@17
pg_isready -h localhost -p 5432
```

### Cloudflare tunnel down
```bash
launchctl unload ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist
```

## 🔑 Ports Reference

| Service | Port | Access |
|---------|------|--------|
| Backend | 8400 | localhost only |
| Frontend | 3400 | localhost only |
| PostgreSQL | 5432 | localhost only |
| Cloudflare | 443 | public via tunnel |

## ⚠️ Remember

- **Dev machine must be on** for PDF access to work
- **Secure SECRET_KEY** is already set in `.env.production`
- **Database password** is default `postgres` - change it!
- **Cloudflare tunnel** provides public HTTPS access
- **No Apache needed** - Cloudflare tunnel handles public access

## 📞 Emergency Contact

If something breaks:
1. Check logs first
2. Verify all services running: `./scripts/health-check.sh`
3. Check PDF mount: `mount | grep dev-pdfs`
4. Restart services in order: database → backend → frontend → tunnel
