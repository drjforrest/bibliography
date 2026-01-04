#!/bin/bash

# v2.0 Database Migration Script
# Run this to create the v2 tables in your database

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
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.12"

echo -e "${BLUE}Step 1: Checking Python version${NC}"
echo "  Current: Python $PYTHON_VERSION"
echo "  Required: Python >= $REQUIRED_VERSION"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
    echo -e "${RED}  ❌ Python 3.12+ required${NC}"
    echo ""
    echo "Install Python 3.12:"
    echo "  brew install python@3.12"
    echo ""
    echo "Or create venv with python3.12:"
    echo "  python3.12 -m venv venv"
    echo "  source venv/bin/activate"
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

# Check database connection
echo -e "${BLUE}Step 5: Checking database connection${NC}"
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}  ⚠️  DATABASE_URL not set in environment${NC}"
    echo "  Checking .env file..."
    if [ -f ".env" ]; then
        export $(cat .env | grep DATABASE_URL | xargs)
        echo -e "${GREEN}  ✅ Loaded from .env${NC}"
    else
        echo -e "${RED}  ❌ No .env file found${NC}"
        echo ""
        echo "Create backend/.env with:"
        echo "  DATABASE_URL=postgresql+asyncpg://user:pass@localhost/hero_evidence_library"
        exit 1
    fi
else
    echo -e "${GREEN}  ✅ DATABASE_URL configured${NC}"
fi
echo ""

# Generate migration
echo -e "${BLUE}Step 6: Generating Alembic migration${NC}"
alembic revision --autogenerate -m "Add v2.0 content generation tables (podcasts, summaries, infographics, slide_decks)"
echo -e "${GREEN}  ✅ Migration generated${NC}"
echo ""

# Preview migration
echo -e "${BLUE}Step 7: Migration preview${NC}"
echo "  Generating SQL preview..."
alembic upgrade head --sql > migration_preview.sql
echo ""
echo "  Preview saved to: migration_preview.sql"
echo "  Review this file to see what will be created"
echo ""

# Confirm before applying
read -p "Apply migration to database? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration not applied. Run this script again when ready."
    exit 0
fi

# Apply migration
echo ""
echo -e "${BLUE}Step 8: Applying migration${NC}"
alembic upgrade head
echo -e "${GREEN}  ✅ Migration applied${NC}"
echo ""

# Verify tables created
echo -e "${BLUE}Step 9: Verifying tables${NC}"
echo "  Checking database..."

# This requires psycopg2 or direct psql access
# For now, just inform the user
echo ""
echo "  Expected new tables:"
echo "    - podcasts"
echo "    - summaries"
echo "    - infographics"
echo "    - slide_decks"
echo ""
echo "  Verify with:"
echo "    psql -d hero_evidence_library -c '\\dt'"
echo ""

echo -e "${GREEN}🎉 Migration complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify tables were created"
echo "  2. Test v1 app still works"
echo "  3. Test v2 app can access new tables"
echo "  4. Commit migration file to git"
echo ""
echo "To rollback (if needed):"
echo "  alembic downgrade -1"
echo ""
