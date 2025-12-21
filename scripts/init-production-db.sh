#!/bin/bash

# Initialize Production Database for hero-evidence-library
# This script runs ON THE PRODUCTION SERVER (mac-mini)
# Creates fresh PostgreSQL database with pgvector extension

set -e

echo "🗄️  Initializing Production Database"
echo "====================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
DB_NAME="hero_evidence_library_prod"
DB_USER="postgres"
DB_PASSWORD="postgres"  # Change this in production!

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 &> /dev/null; then
    print_error "PostgreSQL is not running on localhost:5432"
    print_warning "Start it with: brew services start postgresql@17 (or your version)"
    exit 1
fi

print_status "PostgreSQL is running"

# Check if database already exists
if psql -h localhost -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    print_warning "Database '$DB_NAME' already exists"
    read -p "Do you want to DROP and recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Dropping existing database..."
        psql -h localhost -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
    else
        print_status "Keeping existing database"
        exit 0
    fi
fi

# Create database
print_status "Creating database '$DB_NAME'..."
psql -h localhost -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"

if [ $? -eq 0 ]; then
    print_status "✓ Database created successfully"
else
    print_error "Failed to create database"
    exit 1
fi

# Install pgvector extension
print_status "Installing pgvector extension..."
psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

if [ $? -eq 0 ]; then
    print_status "✓ pgvector extension installed"
else
    print_error "Failed to install pgvector extension"
    print_warning "Make sure pgvector is installed: brew install pgvector"
    exit 1
fi

# Create tables using Alembic migrations
print_status "Running Alembic migrations..."
cd ~/production/hero-evidence-library/backend

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    print_error "Virtual environment not found"
    print_warning "Run deployment script first to set up the environment"
    exit 1
fi

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    print_warning "Alembic not found, installing..."
    pip install alembic
fi

# Run migrations
if [ -d "alembic" ]; then
    print_status "Running database migrations..."
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_status "✓ Database schema created successfully"
    else
        print_error "Failed to run migrations"
        exit 1
    fi
else
    print_warning "No alembic directory found"
    print_status "Creating tables directly from models..."
    
    # Create a Python script to initialize tables
    cat > /tmp/init_db.py << 'PYEOF'
import asyncio
import sys
sys.path.insert(0, '/Users/jforrest/production/hero-evidence-library/backend')

from app.db import Base, engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created successfully")

asyncio.run(init_db())
PYEOF

    python /tmp/init_db.py
    
    if [ $? -eq 0 ]; then
        print_status "✓ Database tables created"
        rm /tmp/init_db.py
    else
        print_error "Failed to create tables"
        exit 1
    fi
fi

# Verify installation
print_status "Verifying database setup..."
TABLES=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLES" -gt 0 ]; then
    print_status "✓ Found $TABLES tables in database"
else
    print_warning "No tables found in database"
fi

# Check for pgvector extension
VECTOR_EXT=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';")

if [ "$VECTOR_EXT" -eq 1 ]; then
    print_status "✓ pgvector extension is active"
else
    print_error "pgvector extension not found"
    exit 1
fi

print_status ""
print_status "🎉 Database initialization complete!"
print_status ""
print_status "Database configuration:"
print_status "  Name: $DB_NAME"
print_status "  Host: localhost"
print_status "  Port: 5432"
print_status "  User: $DB_USER"
print_status ""
print_status "Connection string for .env:"
print_status "  DATABASE_URL=\"postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}\""
print_status ""
print_warning "⚠ Remember to change the database password in production!"
print_status ""
print_status "Next steps:"
print_status "1. Update backend/.env with the connection string above"
print_status "2. Restart backend service: pkill -f uvicorn && cd ~/production/hero-evidence-library/backend && nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8400 &"
print_status "3. Create your first user via the API or web interface"
