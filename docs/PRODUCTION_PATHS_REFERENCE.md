# Production Paths & Commands Reference

Quick reference for all important paths, commands, and configurations used in production deployment.

## Server Access

### SSH Hosts

```bash
# Primary mac-mini access (via Tailscale)
ssh mac-mini

# Production host alias (explicit IP)
ssh production  # IP: 100.107.165.113

# Local network access
ssh mac-mini-local  # IP: 192.168.1.69
```

### SSH Configuration

- **User**: `jforrest`
- **SSH Config**: `~/.ssh/config`
- **SSH Key**: `~/.ssh/Mac-mini` (managed by 1Password)
- **1Password Agent**: `~/.1password/agent.sock`

## Python & Package Management

### Python on mac-mini

```bash
# Python is managed via pyenv
export PYENV_ROOT=~/.pyenv
export PATH=$PYENV_ROOT/shims:$PATH

# Available versions
python3 --version  # 3.12.9 (via pyenv)
~/.pyenv/versions/  # 3.12.9, 3.12.10 installed
```

### Pyenv Paths

- **Root**: `~/.pyenv/`
- **Versions**: `~/.pyenv/versions/`
- **Shims**: `~/.pyenv/shims/`
- **Global version**: `cat ~/.pyenv/version` → `3.12.9`

## Homebrew on mac-mini

### Homebrew Paths

```bash
# Homebrew is at /usr/local (Intel Mac)
/usr/local/bin/brew --version

# Important: Homebrew is NOT in PATH for SSH sessions
# Always use full path: /usr/local/bin/brew
```

### Installed Packages

```bash
/usr/local/bin/brew list | grep -E '(postgresql|pgvector|sshfs|cloudflared)'
# - postgresql@17
# - pgvector
# - sshfs-mac
# - cloudflared
```

## PostgreSQL on mac-mini

### PostgreSQL Paths

```bash
# PostgreSQL 17 installation
/usr/local/opt/postgresql@17/

# Binaries
/usr/local/opt/postgresql@17/bin/pg_isready
/usr/local/opt/postgresql@17/bin/psql
/usr/local/opt/postgresql@17/bin/createdb

# Check status
/usr/local/bin/brew services list | grep postgresql
```

### PostgreSQL Status

```bash
# Service status
/usr/local/bin/brew services list | grep postgresql
# Output: postgresql@17 started jforrest ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist

# Connection test
/usr/local/opt/postgresql@17/bin/pg_isready -h localhost -p 5432
# Output: localhost:5432 - accepting connections
```

### Production Database

- **Database Name**: `hero_evidence_library_prod`
- **User**: `postgres`
- **Host**: `localhost`
- **Port**: `5432`
- **Connection String**: `postgresql+asyncpg://postgres:postgres@localhost:5432/hero_evidence_library_prod`

## Application Paths

### Local Development (drjforrest's laptop)

```
/Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/
├── backend/                 # FastAPI backend
│   ├── .env                # Dev environment config
│   ├── main.py             # Backend entry point
│   ├── app/                # Application code
│   └── data/pdfs/          # PDF storage (dev)
├── frontend/               # Frontend applications
│   └── nextjs-app/         # Next.js frontend
├── docs/                   # Documentation
├── scripts/                # Deployment & utility scripts
├── .env.production         # Production environment config
└── deploy.sh               # Main deployment script
```

### Production (mac-mini)

```
~/production/hero-evidence-library/
├── backend/
│   ├── .env                # Production config (copied from .env.production)
│   └── venv/               # Python virtual environment
├── frontend/nextjs-app/
└── scripts/
```

## Deployment Scripts

### Available Scripts

```bash
# Located in: /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/scripts/

./deploy.sh                          # Main deployment script (run from project root)
./scripts/init-production-db.sh      # Initialize production database
./scripts/setup-pdf-mount.sh         # Set up SSHFS mount for PDFs
./scripts/health-check.sh            # Check service health
./scripts/create-user.sh             # Create application user
./scripts/setup-db.sh                # Database setup
./scripts/import-data.sh             # Import data
./scripts/ingest-from-macbook.sh     # Ingest PDFs from macbook
./scripts/sync-to-macmini.sh         # Legacy sync script
```

## Service Ports

### Production Ports

- **Backend API**: `8400`
- **Frontend**: `3400`
- **PostgreSQL**: `5432`
- **PDF Tunnel**: `9999` (SSH tunnel from dev machine)

### Service URLs

```bash
# Backend API
http://localhost:8400
http://localhost:8400/docs  # API documentation

# Frontend
http://localhost:3400

# Public URL (via Cloudflare)
https://library.counterforce-hero.tech
```

## Environment Files

### Development (.env)

```
Location: /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/backend/.env
Database: postgresql+asyncpg://postgres:postgres@localhost:5432/bibliography_db
PDF Storage: ./data/pdfs
```

### Production (.env.production → backend/.env on mac-mini)

```
Location (dev): /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/.env.production
Location (prod): ~/production/hero-evidence-library/backend/.env
Database: postgresql+asyncpg://postgres:postgres@localhost:5432/hero_evidence_library_prod
PDF Storage: /tmp/dev-pdfs (SSHFS mount)
```

## Log Files (on mac-mini)

### Application Logs

```bash
~/production/hero-evidence-library/hero_evidence_library_backend.log
~/production/hero-evidence-library/hero_evidence_library_frontend.log
```

### Viewing Logs

```bash
# Backend logs
ssh mac-mini "tail -f ~/production/hero-evidence-library/hero_evidence_library_backend.log"

# Frontend logs
ssh mac-mini "tail -f ~/production/hero-evidence-library/hero_evidence_library_frontend.log"
```

## Common Commands

### Deployment Workflow

```bash
# 1. From dev machine - deploy application
./deploy.sh

# 2. Initialize database (first time only)
ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/init-production-db.sh"

# 3. Set up PDF mount (first time only)
ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/setup-pdf-mount.sh"

# 4. Check service health
ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/health-check.sh"
```

### Service Management

```bash
# Check running services
ssh mac-mini "ps aux | grep -E '(uvicorn|next|hero)' | grep -v grep"

# Check ports
ssh mac-mini "lsof -i:8400"  # Backend
ssh mac-mini "lsof -i:3400"  # Frontend

# Restart services (run deploy.sh again)
./deploy.sh
```

### Database Operations

```bash
# Connect to production database
ssh mac-mini "/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod"

# Check database size
ssh mac-mini "/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -c 'SELECT pg_size_pretty(pg_database_size(current_database()));'"

# Count records
ssh mac-mini "/usr/local/opt/postgresql@17/bin/psql -h localhost -U postgres -d hero_evidence_library_prod -c 'SELECT COUNT(*) FROM scientific_papers;'"
```

## DEVONthink Sync

### DEVONthink MCP Configuration

```bash
# Backend .env setting
DEVONTHINK_MCP_BACKEND="real"

# DEVONthink Database
Database: "BIBLIOGRAPHY"
```

### Sync Endpoints

```bash
# Full sync
curl -X POST http://localhost:8400/api/v1/devonthink/sync

# Incremental sync
curl -X POST http://localhost:8400/api/v1/devonthink/sync/incremental

# Check status
curl http://localhost:8400/api/v1/devonthink/sync/status

# Health check
curl http://localhost:8400/api/v1/devonthink/health
```

## Troubleshooting

### SSH Issues

```bash
# Check 1Password SSH agent
SSH_AUTH_SOCK=~/.1password/agent.sock ssh-add -l

# Verify SSH key is loaded
# Should see: Mac-mini (ED25519)
```

### Python/Pyenv Issues on mac-mini

```bash
# Set pyenv environment
ssh mac-mini "export PYENV_ROOT=~/.pyenv && export PATH=\$PYENV_ROOT/shims:\$PATH && python3 --version"
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
ssh mac-mini "/usr/local/opt/postgresql@17/bin/pg_isready -h localhost -p 5432"

# Check service status
ssh mac-mini "/usr/local/bin/brew services list | grep postgresql"
```

## Important Notes

1. **Homebrew is not in PATH**: Always use full path `/usr/local/bin/brew` when running via SSH
2. **Python via pyenv**: Set `PYENV_ROOT` and add shims to PATH for SSH sessions
3. **PostgreSQL paths**: Use `/usr/local/opt/postgresql@17/bin/` prefix for PostgreSQL commands
4. **SSH ciphers**: Mac-mini requires specific ciphers (configured in `~/.ssh/config`)
5. **PDFs stored on dev machine**: Production accesses PDFs via SSHFS mount from dev laptop

## Quick Copy-Paste Commands

### Deploy to production

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
./deploy.sh
```

### Check production status

```bash
ssh mac-mini "cd ~/production/hero-evidence-library && ./scripts/health-check.sh"
```

### View backend API docs

```bash
open http://mac-mini:8400/docs
```

### Run DEVONthink sync

```bash
ssh mac-mini "cd ~/production/hero-evidence-library && source backend/venv/bin/activate && curl -X POST http://localhost:8400/api/v1/devonthink/sync"
```
