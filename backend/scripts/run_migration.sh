#!/bin/bash

# v2.0 Database Migration Script
# Creates v2 tables using SQLAlchemy metadata (same as v1)

set -e  # Exit on error

echo "🗄️  HERO Evidence Library v2.0 - Database Migration"
echo "===================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Python version
echo -e "${BLUE}Step 1: Checking Python version${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Current: Python $PYTHON_VERSION"
echo "  Required: Python >= 3.12"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
    echo -e "${RED}  ❌ Python 3.12+ required${NC}"
    echo ""
    echo "Install Python 3.12:"
    echo "  brew install python@3.12"
    exit 1
fi
echo -e "${GREEN}  ✅ Python version OK${NC}"
echo ""

# Check if venv exists
echo -e "${BLUE}Step 2: Checking virtual environment${NC}"
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}  ✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}  ✅ Virtual environment exists${NC}"
fi
echo ""

# Activate venv
echo -e "${BLUE}Step 3: Activating virtual environment${NC}"
source venv/bin/activate
echo -e "${GREEN}  ✅ Activated${NC}"
echo ""

# Install dependencies
echo -e "${BLUE}Step 4: Installing dependencies${NC}"
echo "  This may take a few minutes..."
pip install -e . > /dev/null 2>&1
echo -e "${GREEN}  ✅ Dependencies installed${NC}"
echo ""

# Check database connection and load ALL env vars
echo -e "${BLUE}Step 5: Loading environment variables${NC}"

# Try .env first, then .env.production
if [ -f ".env" ]; then
    echo "  Loading from .env..."
    set -a
    source .env
    set +a
    echo -e "${GREEN}  ✅ Loaded from .env${NC}"
elif [ -f ".env.production" ]; then
    echo "  Loading from .env.production..."
    set -a
    source .env.production
    set +a
    echo -e "${GREEN}  ✅ Loaded from .env.production${NC}"
else
    echo -e "${RED}  ❌ No .env or .env.production file found${NC}"
    echo ""
    echo "Create backend/.env with required variables"
    exit 1
fi

# Verify DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}  ❌ DATABASE_URL not found in env file${NC}"
    exit 1
fi

echo "  Database: ${DATABASE_URL##*@}"
echo ""

# Preview what will be created
echo -e "${BLUE}Step 6: What will be created${NC}"
echo "  New tables:"
echo "    - podcasts (audio discussions of papers)"
echo "    - summaries (lay, technical, executive summaries)"
echo "    - infographics (visual content generation)"
echo "    - slide_decks (presentation export)"
echo ""
echo "  New enum type:"
echo "    - summarytype (lay, technical, executive, comparative, visual)"
echo ""
echo "  NOTE: All v1 tables remain unchanged"
echo ""

# Confirm before applying
read -p "Create v2 tables in database? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

# Run migration using standalone script (bypasses app config)
echo ""
echo -e "${BLUE}Step 7: Running migration${NC}"

# Export DATABASE_URL for Python script
export DATABASE_URL

# Run the standalone migration script
python3 scripts/create_v2_tables.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 Migration complete!${NC}"
else
    echo ""
    echo -e "${RED}❌ Migration failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Migration complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify tables were created:"
echo "     psql -d hero_evidence_library -c '\\dt'"
echo ""
echo "  2. Test v1 app still works:"
echo "     cd ../hero_evidence_library/backend"
echo "     uvicorn main:app --reload --port 8000"
echo ""
echo "  3. Test v2 app can access tables:"
echo "     cd ../evidence_library_v2/backend"
echo "     uvicorn main:app --reload --port 8001"
echo ""
echo "To verify in database:"
echo "  psql -d hero_evidence_library -c 'SELECT tablename FROM pg_tables WHERE schemaname = '\"'\"'public'\"'\"' ORDER BY tablename;'"
echo ""
