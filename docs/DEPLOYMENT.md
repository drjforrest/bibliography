# hero-evidence-library Production Deployment Guide

This guide covers deploying hero-evidence-library to your mac-mini production server with PDFs accessed via SSHFS mount from your development machine.

## 🎯 Architecture Overview

### Production Setup
- **Server**: mac-mini (production server)
- **Backend**: FastAPI on port 8400
- **Frontend**: Next.js on port 3400
- **Database**: PostgreSQL 17.x on port 5432
- **PDF Storage**: SSHFS mount from dev machine to `/tmp/dev-pdfs`
- **Public Access**: Cloudflare tunnel at `library.counterforce-hero.tech`

### Why SSHFS for PDFs?
This temporary solution allows production to access PDFs on your dev machine without:
- Duplicating large PDF files
- Requiring manual sync processes
- Complex cloud storage setup

**⚠️ Note**: This requires your dev machine to be powered on and accessible on the network. For long-term production, consider migrating to cloud storage (S3/MinIO).

---

## 📋 Prerequisites

### On Dev Machine (Your Laptop)
- [x] Python 3.12+
- [x] Node.js 22+
- [x] SSH access to mac-mini configured
- [ ] Remote Login enabled (for SSHFS mount)
- [ ] PDFs in `backend/data/pdfs/`

### On Production Server (mac-mini)
- [ ] Python 3.12 (currently has 3.9.6, needs upgrade)
- [x] Node.js via nvm
- [ ] PostgreSQL 17.x with pgvector
- [ ] Homebrew installed
- [ ] SSH keys set up to access dev machine

---

## 🚀 Step-by-Step Deployment

### Phase 1: Pre-Deployment Setup

#### 1.1 Install Python 3.12 on mac-mini

```bash
# SSH to mac-mini
ssh mac-mini

# Install Python 3.12 via Homebrew
brew install python@3.12

# Verify installation
python3.12 --version  # Should show 3.12.x

# Set as default (optional)
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### 1.2 Install PostgreSQL with pgvector on mac-mini

```bash
# On mac-mini
brew install postgresql@17 pgvector

# Start PostgreSQL
brew services start postgresql@17

# Verify it's running
pg_isready -h localhost -p 5432
```

#### 1.3 Enable Remote Login on Dev Machine

```bash
# On your dev machine (laptop)
# Go to System Settings > General > Sharing
# Enable "Remote Login"
# Or via command line:
sudo systemsetup -setremotelogin on
```

#### 1.4 Set Up SSH Keys (mac-mini → dev machine)

```bash
# On mac-mini, generate SSH key if needed
ssh-keygen -t ed25519 -C "jforrest@mac-mini"

# Copy public key to dev machine
ssh-copy-id drjforrest@drjforrest-laptop.local

# Test connection
ssh drjforrest@drjforrest-laptop.local "echo 'Connection successful'"
```

#### 1.5 Update Production Environment File

```bash
# On your dev machine, edit .env.production
# Update these critical values:

SECRET_KEY="<generate-secure-random-key>"  # Use: openssl rand -hex 32

# Add any API keys you use
OPENAI_API_KEY="sk-..."
```

### Phase 2: Initial Deployment

#### 2.1 Deploy Application Code

```bash
# On your dev machine, from project root
./deploy.sh
```

This script will:
- ✅ Build Next.js frontend
- ✅ Sync code to mac-mini (excluding PDFs)
- ✅ Copy `.env.production` to backend/.env
- ✅ Install Python dependencies on mac-mini
- ✅ Install Node.js dependencies on mac-mini
- ✅ Start backend on port 8400
- ✅ Start frontend on port 3400

**Expected Output:**
```
🔍 hero-evidence-library Production Deployment
==============================================
[INFO] Building frontend...
[INFO] Syncing local changes to production...
[INFO] Setting up production environment...
[INFO] ✓ Backend started (PID: 12345)
[INFO] ✓ Frontend started (PID: 12346)
🎉 Deployment complete!
```

#### 2.2 Initialize Production Database

```bash
# SSH to mac-mini
ssh mac-mini

# Navigate to project
cd ~/production/hero-evidence-library

# Run database initialization
./scripts/init-production-db.sh
```

This will:
- ✅ Create database `hero_evidence_library_prod`
- ✅ Install pgvector extension
- ✅ Run migrations/create tables
- ✅ Verify setup

#### 2.3 Set Up PDF Access via SSHFS

```bash
# Still on mac-mini
cd ~/production/hero-evidence-library

# Run SSHFS mount setup
./scripts/setup-pdf-mount.sh
```

**Important:** When prompted, choose **Yes** to create LaunchAgent for auto-mounting on startup.

**Verify PDF access:**
```bash
# On mac-mini
ls /tmp/dev-pdfs
# Should show your PDF directories (e.g., 2025/01/)
```

### Phase 3: Configure Cloudflare Tunnel

#### 3.1 Set Up Cloudflare Tunnel

```bash
# On mac-mini
# Install cloudflared if not already installed
brew install cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create hero-evidence-library

# Configure tunnel
cat > ~/.cloudflared/config.yml << EOF
tunnel: <TUNNEL_ID>
credentials-file: /Users/jforrest/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: library.counterforce-hero.tech
    service: http://localhost:3400
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run hero-evidence-library
```

#### 3.2 Create LaunchAgent for Cloudflare Tunnel

```bash
# On mac-mini
cat > ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudflare.tunnel.hero-evidence-library</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/cloudflared</string>
        <string>tunnel</string>
        <string>run</string>
        <string>hero-evidence-library</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/cloudflared-error.log</string>
    <key>StandardOutPath</key>
    <string>/tmp/cloudflared.log</string>
</dict>
</plist>
EOF

# Load LaunchAgent
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist
```

#### 3.3 Update DNS

In Cloudflare Dashboard:
1. Go to your domain `counterforce-hero.tech`
2. Add CNAME record:
   - Name: `library`
   - Target: `<TUNNEL_ID>.cfargotunnel.com`
   - Proxied: Yes (orange cloud)

---

## 🔧 Management & Maintenance

### Check Service Status

```bash
# On mac-mini
# Check backend
lsof -i:8400

# Check frontend
lsof -i:3400

# Check database
pg_isready -h localhost -p 5432

# Check PDF mount
mount | grep /tmp/dev-pdfs

# View logs
tail -f ~/production/hero-evidence-library/hero_evidence_library_backend.log
tail -f ~/production/hero-evidence-library/hero_evidence_library_frontend.log
```

### Restart Services

```bash
# On mac-mini
cd ~/production/hero-evidence-library

# Restart backend
pkill -f "uvicorn.*8400"
cd backend
source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8400 > ../hero_evidence_library_backend.log 2>&1 &

# Restart frontend
pkill -f "next.*3400"
cd frontend/nextjs-app
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
nvm use 22
nohup npm run start -- -p 3400 > ../../hero_evidence_library_frontend.log 2>&1 &
```

### Re-Deploy After Changes

```bash
# On your dev machine
./deploy.sh
```

This will sync changes and restart services automatically.

### Remount PDFs (if connection lost)

```bash
# On mac-mini
# Unmount first
umount /tmp/dev-pdfs

# Remount
./scripts/setup-pdf-mount.sh
```

---

## 🐛 Troubleshooting

### Backend Won't Start

**Check logs:**
```bash
tail -50 ~/production/hero-evidence-library/hero_evidence_library_backend.log
```

**Common issues:**
- Database connection failed → Check PostgreSQL is running
- Import errors → Reinstall dependencies in venv
- Port already in use → Kill existing process

### Frontend Won't Build/Start

**Check Node version:**
```bash
node --version  # Should be v22.x
```

**If wrong version:**
```bash
nvm install 22
nvm use 22
nvm alias default 22
```

### Database Connection Issues

**Test connection:**
```bash
psql -U postgres -d hero_evidence_library_prod -c "SELECT 1;"
```

**Reset database:**
```bash
ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/init-production-db.sh"
```

### PDF Access Issues

**Check mount:**
```bash
# On mac-mini
mount | grep dev-pdfs
ls -la /tmp/dev-pdfs
```

**Check SSH to dev machine:**
```bash
ssh drjforrest@drjforrest-laptop.local "ls ~/dev/hero-counterforce/hero_evidence_library/backend/data/pdfs"
```

**Remount:**
```bash
umount /tmp/dev-pdfs
./scripts/setup-pdf-mount.sh
```

### Cloudflare Tunnel Not Working

**Check tunnel status:**
```bash
cloudflared tunnel info hero-evidence-library
```

**Check tunnel process:**
```bash
ps aux | grep cloudflared
```

**View logs:**
```bash
tail -f /tmp/cloudflared.log
tail -f /tmp/cloudflared-error.log
```

**Restart tunnel:**
```bash
launchctl unload ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist
```

---

## 🔐 Security Considerations

### Important Security Updates

1. **Change Database Password**
   ```bash
   # On mac-mini
   psql -U postgres
   ALTER USER postgres PASSWORD 'new-secure-password';
   \q
   
   # Update .env
   nano ~/production/hero-evidence-library/backend/.env
   # Update DATABASE_URL with new password
   ```

2. **Update SECRET_KEY**
   ```bash
   # Generate new secret
   openssl rand -hex 32
   
   # Update in .env.production and redeploy
   ```

3. **Secure SSH Keys**
   - Use strong passphrases
   - Limit SSH access by IP if possible
   - Regularly rotate keys

4. **Firewall Configuration**
   ```bash
   # On mac-mini, ensure only Cloudflare can access ports
   # Ports 8400 and 3400 should only be accessible from localhost
   ```

---

## 📊 Monitoring

### Set Up Basic Monitoring

```bash
# Create monitoring script
cat > ~/production/hero-evidence-library/scripts/health-check.sh << 'EOF'
#!/bin/bash

echo "🏥 Health Check $(date)"
echo "========================"

# Check backend
if curl -s http://localhost:8400/health >/dev/null; then
    echo "✓ Backend is healthy"
else
    echo "✗ Backend is down"
fi

# Check frontend
if curl -s http://localhost:3400 >/dev/null; then
    echo "✓ Frontend is healthy"
else
    echo "✗ Frontend is down"
fi

# Check database
if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "✓ Database is healthy"
else
    echo "✗ Database is down"
fi

# Check PDF mount
if [ -d "/tmp/dev-pdfs" ] && [ "$(ls -A /tmp/dev-pdfs)" ]; then
    echo "✓ PDF mount is healthy"
else
    echo "✗ PDF mount is down"
fi
EOF

chmod +x ~/production/hero-evidence-library/scripts/health-check.sh

# Run health check
./scripts/health-check.sh
```

---

## 🚀 Future Improvements

### Migrate to Cloud Storage

When ready to eliminate dev machine dependency:

1. **Set up MinIO or S3**
2. **Migrate PDFs**: Use `aws s3 sync` or similar
3. **Update configuration**: Point `PDF_STORAGE_ROOT` to cloud storage
4. **Remove SSHFS mount**: No longer needed

### Add Redis for Caching

```bash
# On mac-mini
brew install redis
brew services start redis

# Update .env
REDIS_URL="redis://localhost:6379/0"
```

### Set Up Automated Backups

```bash
# Create backup script
cat > ~/production/hero-evidence-library/scripts/backup-db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U postgres hero_evidence_library_prod | gzip > ~/backups/hero_evidence_${DATE}.sql.gz
EOF

chmod +x ~/production/hero-evidence-library/scripts/backup-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * ~/production/hero-evidence-library/scripts/backup-db.sh
```

---

## 📞 Support

If you encounter issues not covered in this guide:

1. Check logs first (backend, frontend, cloudflared)
2. Verify all services are running
3. Test network connectivity between dev and prod
4. Review recent changes that might have caused issues

**Quick Reference URLs:**
- Frontend: http://localhost:3400 (on mac-mini)
- Backend: http://localhost:8400 (on mac-mini)
- API Docs: http://localhost:8400/docs
- Public: https://library.counterforce-hero.tech

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Python 3.12 installed on mac-mini
- [ ] PostgreSQL 17 with pgvector installed
- [ ] SSH keys configured (both directions)
- [ ] Remote Login enabled on dev machine
- [ ] `.env.production` configured with secure keys

### Initial Deployment
- [ ] Run `./deploy.sh` from dev machine
- [ ] Run `./scripts/init-production-db.sh` on mac-mini
- [ ] Run `./scripts/setup-pdf-mount.sh` on mac-mini
- [ ] Verify services running (backend, frontend, db)
- [ ] Verify PDF access from production

### Cloudflare Setup
- [ ] Cloudflare tunnel created and configured
- [ ] LaunchAgent created for auto-start
- [ ] DNS CNAME record added
- [ ] Public URL accessible

### Post-Deployment
- [ ] Change database password
- [ ] Update SECRET_KEY
- [ ] Create first user account
- [ ] Test PDF upload/retrieval
- [ ] Set up monitoring/health checks
- [ ] Configure automated backups

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
