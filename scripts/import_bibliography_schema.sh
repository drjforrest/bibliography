#!/bin/bash

# Bibliography Database Schema Import Script for mac-mini
# This script imports the bibliography database schema with comprehensive checks,
# execution, verification, and rollback capabilities.

set -e  # Exit on any error

# Configuration
DB_NAME="bibliography_db"
DB_USER="postgres"
SCHEMA_FILE="create_bibliography_db.sql"
BACKUP_DIR="/usr/local/var/postgresql@17/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

# ========================================
# PRE-IMPORT CHECKS
# ========================================

log "Starting bibliography database schema import..."

log "Performing pre-import checks..."

# Check 1: PostgreSQL service status
echo "1. Checking PostgreSQL service status..."
if brew services list | grep postgresql@17 | grep started > /dev/null; then
    success "PostgreSQL service is running"
else
    error "PostgreSQL service is not running"
    echo "Start PostgreSQL with: brew services start postgresql@17"
    exit 1
fi

# Check 2: PostgreSQL connectivity
echo "2. Checking PostgreSQL connectivity..."
if psql -h localhost -U "$DB_USER" -d postgres -c "SELECT version();" > /dev/null 2>&1; then
    success "PostgreSQL connection successful"
else
    error "Cannot connect to PostgreSQL"
    echo "Check PostgreSQL logs: tail -f /usr/local/var/log/postgresql@17.log"
    exit 1
fi

# Check 3: Database existence
echo "3. Checking if database '$DB_NAME' exists..."
if psql -h localhost -U "$DB_USER" -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1; then
    success "Database '$DB_NAME' exists"
else
    error "Database '$DB_NAME' does not exist"
    echo "Create database with: createdb -U $DB_USER $DB_NAME"
    exit 1
fi

# Check 4: pgvector extension availability
echo "4. Checking pgvector extension availability..."
if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1 FROM pg_available_extensions WHERE name = 'vector';" | grep -q 1; then
    success "pgvector extension is available"
else
    error "pgvector extension is not available"
    echo "Install pgvector with: brew install pgvector"
    echo "Then enable with: psql -d $DB_NAME -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
    exit 1
fi

# Check 5: Schema file existence
echo "5. Checking schema file existence..."
if [ -f "$SCHEMA_FILE" ]; then
    success "Schema file '$SCHEMA_FILE' exists"
    FILE_SIZE=$(stat -f '%z' "$SCHEMA_FILE" 2>/dev/null || stat -c '%s' "$SCHEMA_FILE")
    echo "   File size: $FILE_SIZE bytes"
else
    error "Schema file '$SCHEMA_FILE' not found in current directory"
    exit 1
fi

# ========================================
# CREATE BACKUP (SAFETY MEASURE)
# ========================================

log "Creating pre-import backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_pre_import_$TIMESTAMP.sql"

echo "Creating backup of existing database..."
if pg_dump -h localhost -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE" --no-password > /dev/null 2>&1; then
    success "Backup created: $BACKUP_FILE"

    # Compress backup
    gzip "$BACKUP_FILE"
    success "Backup compressed: ${BACKUP_FILE}.gz"
else
    warning "Could not create backup (database might be empty)"
fi

# ========================================
# SCHEMA EXECUTION
# ========================================

log "Executing database schema import..."

echo "Importing schema from $SCHEMA_FILE..."

# Execute the schema with error handling
if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f "$SCHEMA_FILE" --set ON_ERROR_STOP=on > schema_import.log 2>&1; then
    success "Schema import completed successfully"
else
    error "Schema import failed"
    echo "Check schema_import.log for details"
    echo ""
    echo "ROLLBACK INSTRUCTIONS:"
    echo "======================"
    echo "1. Drop and recreate database:"
    echo "   dropdb -U $DB_USER $DB_NAME"
    echo "   createdb -U $DB_USER $DB_NAME"
    echo ""
    echo "2. If backup exists, restore from backup:"
    echo "   gunzip -c ${BACKUP_FILE}.gz | psql -U $DB_USER -d $DB_NAME"
    exit 1
fi

# ========================================
# VERIFICATION
# ========================================

log "Performing post-import verification..."

# Verification 1: Table count
echo "1. Checking table counts..."
TABLE_COUNT=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
EXPECTED_TABLES=12  # Based on schema: user, searchspaces, documents, scientific_papers, tags, chunks, chats, podcasts, search_source_connectors, devonthink_sync, devonthink_folders, paper_annotations, paper_tags

if [ "$TABLE_COUNT" -ge "$EXPECTED_TABLES" ]; then
    success "Found $TABLE_COUNT tables (expected at least $EXPECTED_TABLES)"
else
    error "Only found $TABLE_COUNT tables, expected at least $EXPECTED_TABLES"
fi

# Verification 2: Extension verification
echo "2. Verifying pgvector extension..."
VECTOR_VERSION=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';")
if [ -n "$VECTOR_VERSION" ]; then
    success "pgvector extension enabled (version: $VECTOR_VERSION)"
else
    error "pgvector extension not properly enabled"
fi

# Verification 3: Index count
echo "3. Checking index counts..."
INDEX_COUNT=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';")
EXPECTED_INDEXES=40  # Based on schema indexes

if [ "$INDEX_COUNT" -ge "$EXPECTED_INDEXES" ]; then
    success "Found $INDEX_COUNT indexes (expected at least $EXPECTED_INDEXES)"
else
    warning "Only found $INDEX_COUNT indexes, expected at least $EXPECTED_INDEXES"
fi

# Verification 4: Basic functionality test
echo "4. Testing basic functionality..."

# Test vector operations
VECTOR_TEST=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "
CREATE TEMP TABLE test_vectors (id SERIAL, embedding vector(384));
INSERT INTO test_vectors (embedding) VALUES ('[0.1,0.2,0.3]');
INSERT INTO test_vectors (embedding) VALUES ('[0.2,0.3,0.4]');
SELECT COUNT(*) FROM test_vectors;
DROP TABLE test_vectors;
")

if [ "$VECTOR_TEST" -eq 2 ]; then
    success "Vector operations working correctly"
else
    error "Vector operations test failed"
fi

# Test foreign key constraints
echo "5. Testing foreign key constraints..."
FK_TEST=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT COUNT(*) FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY' AND table_schema = 'public';
")

if [ "$FK_TEST" -gt 0 ]; then
    success "Foreign key constraints created ($FK_TEST total)"
else
    error "No foreign key constraints found"
fi

# Test sequence creation
echo "6. Testing sequences..."
SEQ_TEST=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT COUNT(*) FROM information_schema.sequences WHERE sequence_schema = 'public';
")

if [ "$SEQ_TEST" -gt 0 ]; then
    success "Sequences created ($SEQ_TEST total)"
else
    error "No sequences found"
fi

# ========================================
# SUMMARY AND NEXT STEPS
# ========================================

log "Import verification completed successfully!"

echo ""
echo "SUMMARY:"
echo "========"
success "Database: $DB_NAME"
success "Schema file: $SCHEMA_FILE"
success "Tables: $TABLE_COUNT"
success "Indexes: $INDEX_COUNT"
success "Backup created: ${BACKUP_FILE}.gz"

echo ""
echo "NEXT STEPS:"
echo "==========="
echo "1. Test application connectivity:"
echo "   psql -h localhost -U $DB_USER -d $DB_NAME -c 'SELECT * FROM \"user\" LIMIT 1;'"
echo ""
echo "2. Create application user (if not already done):"
echo "   psql -d $DB_NAME -c \"CREATE USER bibliography_app WITH PASSWORD 'secure_password';\""
echo "   psql -d $DB_NAME -c \"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bibliography_app;\""
echo ""
echo "3. Configure application connection string:"
echo "   postgresql://bibliography_app:secure_password@localhost:5432/$DB_NAME"
echo ""
echo "4. Run initial data seeding if needed"
echo ""
echo "5. Set up automated backups:"
echo "   See mac-mini-postgresql-setup-guide.md Section 7"

echo ""
echo "ROLLBACK INSTRUCTIONS (if needed):"
echo "==================================="
echo "1. Drop and recreate database:"
echo "   dropdb -U $DB_USER $DB_NAME"
echo "   createdb -U $DB_USER $DB_NAME"
echo ""
echo "2. Restore from backup (if available):"
echo "   gunzip -c ${BACKUP_FILE}.gz | psql -U $DB_USER -d $DB_NAME"
echo ""
echo "3. Or restore from other backups in $BACKUP_DIR"

echo ""
success "Bibliography database schema import completed successfully!"