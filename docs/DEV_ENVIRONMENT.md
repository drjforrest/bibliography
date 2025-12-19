# Development Environment Guide

## Quick Start

**One command to start everything:**
```bash
./dev.sh
```

That's it! The script will:
- ✅ Check all prerequisites
- ✅ Start the FastAPI backend on http://localhost:8000
- ✅ Start the Next.js frontend on http://localhost:3000
- ✅ Show you helpful logs
- ✅ Shut down gracefully with Ctrl+C

## Prerequisites

Before running the dev environment, ensure you have:

- **Python 3.12+**
- **Node.js 18+**
- **PostgreSQL 14+** with pgvector extension
- **Git**

### Install PostgreSQL (macOS)

```bash
brew install postgresql@14 pgvector
brew services start postgresql@14
```

### Create Database

```bash
createdb bibliography_db
psql bibliography_db -c "CREATE EXTENSION vector;"
```

## First Time Setup

### 1. Clone and Install

```bash
# You've already done this!
cd bibliography
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required `.env` variables:
```bash
DATABASE_URL=postgresql+asyncpg://localhost/bibliography_db
SECRET_KEY=your-secret-key-here
AUTH_TYPE=basic
EMBEDDING_MODEL=openai://nomic-embed-text
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama
PDF_STORAGE_ROOT=./data/pdfs
WATCHED_FOLDER=./data/watched
```

### 3. Frontend Setup

```bash
cd ../frontend/nextjs-app

# Install dependencies
npm install

# Environment file will be auto-created by dev.sh
# Or create manually:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 4. Initialize Database

```bash
# From project root
./scripts/setup-db.sh
```

This creates all tables and indexes.

### 5. Create Your First User

**Option A: While backend is running**
```bash
./scripts/create-user.sh
```

**Option B: Via API docs**
1. Start backend: `./dev.sh --backend`
2. Visit http://localhost:8000/docs
3. Use POST `/auth/register` endpoint

### 6. Import Your Data

```bash
# Test with 10 records
./scripts/import-data.sh --limit 10

# Import all 250 records
./scripts/import-data.sh
```

## Development Scripts

### Main Development Script

```bash
./dev.sh              # Start both backend and frontend
./dev.sh --backend    # Start only backend
./dev.sh --frontend   # Start only frontend
./dev.sh --check      # Run prerequisite checks only
./dev.sh --help       # Show help
```

### Helper Scripts

All in `./scripts/` directory:

**Database Setup**
```bash
./scripts/setup-db.sh        # Initialize database
```

**User Management**
```bash
./scripts/create-user.sh     # Create a user interactively
```

**Data Import**
```bash
./scripts/import-data.sh               # Import all data
./scripts/import-data.sh --dry-run     # Test without importing
./scripts/import-data.sh --limit 10    # Import 10 records
```

**Health Check**
```bash
./scripts/health-check.sh    # Check if services are running
```

## URLs

### Backend

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Interactive Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

### Frontend

- **Web App**: http://localhost:3000
- **Login**: http://localhost:3000/auth/login
- **Register**: http://localhost:3000/auth/register

### Database

- **Host**: localhost
- **Port**: 5432
- **Database**: bibliography_db

## Project Structure

```
bibliography/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── db.py           # Database models
│   │   ├── routes/         # API endpoints
│   │   ├── services/       # Business logic
│   │   └── schemas/        # Pydantic models
│   ├── scripts/            # Utility scripts
│   ├── main.py             # FastAPI entry point
│   └── .env                # Environment variables
│
├── frontend/
│   └── nextjs-app/         # Next.js frontend
│       ├── app/            # Pages and layouts
│       ├── components/     # React components
│       ├── lib/            # Utilities and API client
│       ├── types/          # TypeScript types
│       └── .env.local      # Frontend environment
│
├── data/                   # Your imported data
│   ├── thumbnail_index.csv
│   └── DEVONthink_Thumbnails/
│
├── scripts/                # Development scripts
│   ├── setup-db.sh
│   ├── create-user.sh
│   ├── import-data.sh
│   └── health-check.sh
│
├── logs/                   # Runtime logs (created automatically)
│   ├── backend.log
│   └── frontend.log
│
└── dev.sh                  # Main dev startup script
```

## Daily Development Workflow

### Starting Your Day

```bash
# 1. Pull latest changes
git pull

# 2. Update dependencies if needed
cd backend && source venv/bin/activate && pip install -e . && cd ..
cd frontend/nextjs-app && npm install && cd ../..

# 3. Start everything
./dev.sh
```

### During Development

**View Logs**
```bash
# All logs in one terminal
tail -f logs/backend.log logs/frontend.log

# Separate terminals
tail -f logs/backend.log    # Backend only
tail -f logs/frontend.log   # Frontend only
```

**Check Service Health**
```bash
./scripts/health-check.sh
```

**Restart a Service**
```bash
# Stop all (Ctrl+C)
# Then start specific service:
./dev.sh --backend
# or
./dev.sh --frontend
```

### Ending Your Day

```bash
# Press Ctrl+C in the terminal running ./dev.sh
# The script will gracefully shut down both services
```

## Common Tasks

### Adding a New API Endpoint

1. Create route in `backend/app/routes/`
2. Add service logic in `backend/app/services/`
3. Define schemas in `backend/app/schemas/`
4. Test at http://localhost:8000/docs

Backend auto-reloads on file changes!

### Adding a New Frontend Component

1. Create component in `frontend/nextjs-app/components/`
2. Use TypeScript types from `types/index.ts`
3. Import and use in pages

Frontend auto-reloads on file changes!

### Making Database Changes

1. Update models in `backend/app/db.py`
2. Restart backend (or it will auto-reload)
3. For production, you'd use Alembic migrations

### Adding API Methods to Frontend

1. Add TypeScript types in `types/index.ts`
2. Add method to `lib/api.ts`
3. Use in components with `import { api } from '@/lib/api'`

## Troubleshooting

### "PostgreSQL is not running"

```bash
brew services start postgresql@14
# or
pg_ctl -D /usr/local/var/postgres start
```

### "Backend failed to start"

Check logs:
```bash
cat logs/backend.log
```

Common issues:
- Database not running
- Missing environment variables in `.env`
- Port 8000 already in use

### "Frontend failed to start"

Check logs:
```bash
cat logs/frontend.log
```

Common issues:
- Port 3000 already in use
- Missing dependencies (run `npm install`)
- Missing `.env.local`

### "Cannot connect to API"

1. Check backend is running: `./scripts/health-check.sh`
2. Check CORS settings in `backend/app/app.py`
3. Verify `NEXT_PUBLIC_API_URL` in `frontend/nextjs-app/.env.local`

### Database Connection Errors

Check your `DATABASE_URL` in `backend/.env`:
```bash
DATABASE_URL=postgresql+asyncpg://localhost/bibliography_db
```

Test connection:
```bash
psql bibliography_db -c "SELECT 1"
```

### Port Already in Use

**Backend (8000)**
```bash
lsof -ti:8000 | xargs kill -9
```

**Frontend (3000)**
```bash
lsof -ti:3000 | xargs kill -9
```

## Tips and Tricks

### Multiple Terminal Setup

Recommended terminal layout:

**Terminal 1**: Development environment
```bash
./dev.sh
```

**Terminal 2**: Live logs
```bash
tail -f logs/backend.log logs/frontend.log
```

**Terminal 3**: Database queries, git, etc.
```bash
psql bibliography_db
```

### Quick Database Access

```bash
# Connect to database
psql bibliography_db

# Useful queries
\dt                           # List tables
SELECT COUNT(*) FROM scientific_papers;
SELECT * FROM tags;
\q                           # Quit
```

### Quick API Testing

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your@email.com&password=yourpassword" \
  | jq -r '.access_token')

# Use token
curl http://localhost:8000/api/v1/papers/ \
  -H "Authorization: Bearer $TOKEN"
```

### Environment Variables Quick Reference

**Backend** (`backend/.env`):
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret (generate with `openssl rand -hex 32`)
- `AUTH_TYPE` - Authentication type (basic/google)
- `EMBEDDING_MODEL` - Semantic search model
- `PDF_STORAGE_ROOT` - PDF file storage location

**Frontend** (`frontend/nextjs-app/.env.local`):
- `NEXT_PUBLIC_API_URL` - Backend API URL

## Getting Help

### Documentation

- **API Docs**: http://localhost:8000/docs (when backend is running)
- **Integration Guide**: `./INTEGRATION_GUIDE.md`
- **Tags System**: `./TAGS_SYSTEM_GUIDE.md`
- **Data Import**: `./DATA_IMPORT_GUIDE.md`

### Logs

Always check logs first:
```bash
tail -f logs/backend.log logs/frontend.log
```

### Health Check

```bash
./scripts/health-check.sh
```

## Next Steps

1. ✅ **Set up environment**: Run `./dev.sh`
2. ✅ **Create user**: Run `./scripts/create-user.sh`
3. ✅ **Import data**: Run `./scripts/import-data.sh`
4. 🎨 **Customize UI**: Edit components in `frontend/nextjs-app/components/`
5. 🏷️ **Add tags**: Create tag hierarchy via API or UI
6. 📝 **Add annotations**: Test collaborative features
7. 🔍 **Test search**: Try semantic search on your papers

Happy coding! 🚀
