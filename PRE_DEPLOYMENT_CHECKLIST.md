# 🚦 Pre-Deployment Checklist

Complete these steps **before** running `./deploy.sh` for the first time.

## ✅ Development Machine (Your Laptop)

### System Configuration
- [ ] **Python 3.12** installed and accessible
  ```bash
  python3 --version  # Should show 3.12.x ✅
  ```

- [ ] **Node.js 22** installed and accessible
  ```bash
  node --version  # Should show v22.x ✅
  ```

- [ ] **SSH to mac-mini** works
  ```bash
  ssh mac-mini "echo 'Connected!'"  # Should work ✅
  ```

- [ ] **Remote Login enabled** (for SSHFS reverse connection)
  ```bash
  # System Settings > General > Sharing > Remote Login: ON
  sudo systemsetup -getremotelogin  # Should show "On"
  ```

### Project Configuration
- [ ] **Environment file updated** with your API keys
  ```bash
  # Edit .env.production and add:
  # - OPENAI_API_KEY (if using OpenAI)
  # - Other API keys as needed
  ```

- [ ] **PDFs present** in backend/data/pdfs/
  ```bash
  ls backend/data/pdfs/  # Should show your PDF files/folders
  ```

- [ ] **Project builds successfully**
  ```bash
  cd frontend/nextjs-app && npm install && npm run build
  # Should complete without errors
  ```

---

## ✅ Production Server (mac-mini)

### Prerequisites to Install

Log into mac-mini: `ssh mac-mini`

- [ ] **Python 3.12** installed
  ```bash
  brew install python@3.12
  python3.12 --version  # Should show 3.12.x
  
  # Optional: Set as default
  echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
  source ~/.zshrc
  ```

- [ ] **PostgreSQL 17 with pgvector** installed
  ```bash
  brew install postgresql@17 pgvector
  brew services start postgresql@17
  pg_isready -h localhost -p 5432  # Should show "accepting connections"
  ```

- [ ] **Node.js via nvm** available
  ```bash
  nvm --version  # Should show version (already installed ✅)
  nvm install 22
  nvm use 22
  nvm alias default 22
  ```

- [ ] **SSHFS installed** (for PDF mounting)
  ```bash
  brew install macfuse sshfs
  # May need to allow kernel extension in System Settings > Privacy & Security
  ```

- [ ] **Cloudflared installed** (for tunnel)
  ```bash
  brew install cloudflared
  cloudflared --version
  ```

### SSH Keys Setup

- [ ] **SSH key exists** on mac-mini
  ```bash
  # On mac-mini
  ls ~/.ssh/id_*.pub  # Should show public key
  # If not:
  ssh-keygen -t ed25519 -C "jforrest@mac-mini"
  ```

- [ ] **Can SSH back to dev machine**
  ```bash
  # On mac-mini, test connection to your laptop
  ssh drjforrest@drjforrest-laptop.local "echo 'Success!'"
  # If fails, run on dev machine:
  # ssh-copy-id is not needed, just verify dev machine is accessible
  ```

### Directory Structure

- [ ] **Production directory exists**
  ```bash
  # On mac-mini
  mkdir -p ~/production
  ls -ld ~/production  # Should exist
  ```

---

## 🔐 Security Setup

- [ ] **Secure SECRET_KEY** already set in `.env.production` ✅
  ```
  Already generated: 0bf0bb329406c2b79b0d3378d7a074f7471b6015e2da0d3415bfd562109102cf
  ```

- [ ] **Plan to change database password** after initial setup
  ```
  Default is 'postgres' - change after first deployment!
  ```

- [ ] **API keys** secured in .env.production (not in git)
  ```bash
  # Verify .env.production is in .gitignore
  grep -q ".env.production" .gitignore && echo "✓ Safe" || echo "✗ Add to .gitignore!"
  ```

---

## 🌐 Domain/DNS Setup

- [ ] **Cloudflare account** ready
- [ ] **Domain** `counterforce-hero.tech` accessible
- [ ] **Plan to set up** tunnel after first deployment
  ```
  Will configure: library.counterforce-hero.tech → mac-mini:3400
  ```

---

## 📋 Final Checks

- [ ] **Deployment scripts** are executable
  ```bash
  ls -l deploy.sh scripts/*.sh | grep "^-rwx"  # Should show execute permissions ✅
  ```

- [ ] **Documentation** reviewed
  - [ ] Read `DEPLOYMENT.md` for full process
  - [ ] Bookmarked `QUICKREF.md` for quick commands
  
- [ ] **Backup plan** in place
  ```
  Database can be recreated fresh if needed (starting fresh anyway)
  PDFs remain on dev machine (safe)
  Code is in git (safe)
  ```

---

## 🚀 Ready to Deploy?

If all boxes above are checked, you're ready!

### Next Steps:

1. **First Deployment** (from dev machine):
   ```bash
   ./deploy.sh
   ```

2. **Initialize Database** (on mac-mini):
   ```bash
   ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/init-production-db.sh"
   ```

3. **Set up PDF Mount** (on mac-mini):
   ```bash
   ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/setup-pdf-mount.sh"
   ```

4. **Configure Cloudflare Tunnel** (on mac-mini):
   - Follow steps in `DEPLOYMENT.md` Phase 3

5. **Verify Everything Works**:
   ```bash
   # Check services
   ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/health-check.sh"
   
   # Test public access
   curl https://library.counterforce-hero.tech
   ```

---

## ⚠️ Common Pre-Deployment Issues

### "Python 3.12 not found" on mac-mini
**Solution**: Install via Homebrew (see checklist above)

### "Cannot connect to dev machine" from mac-mini
**Solution**: 
1. Enable Remote Login on dev machine
2. Verify dev machine hostname: `hostname`
3. Try IP address instead of hostname

### "pgvector extension not found"
**Solution**: 
```bash
brew install pgvector
# Then reinitialize database
```

### "Permission denied" for deployment
**Solution**:
```bash
chmod +x deploy.sh
chmod +x scripts/*.sh
```

---

## 📞 Help

If stuck on any checklist item:
1. See detailed instructions in `DEPLOYMENT.md`
2. Check specific error messages
3. Verify network connectivity between machines

**You're doing great! Take it step by step.** 🎯
