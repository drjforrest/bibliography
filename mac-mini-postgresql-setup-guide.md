# PostgreSQL with pgvector Setup Guide for mac-mini

## Overview

This comprehensive guide provides detailed instructions for setting up PostgreSQL 17+ with pgvector extension 0.8.1+ on macOS for the bibliography project mac-mini deployment. The setup matches the development environment requirements and includes production-ready security configurations.

## Prerequisites

- macOS (mac-mini)
- Administrator privileges
- Internet connection for downloads
- At least 4GB free disk space

## Section 1: PostgreSQL Installation

### Install PostgreSQL using Homebrew

Homebrew is the recommended package manager for macOS installations.

```bash
# Install Homebrew (if not already installed)
# Visit https://brew.sh/ and follow installation instructions
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Update Homebrew
brew update

# Install PostgreSQL 17
brew install postgresql@17

# Start PostgreSQL service
brew services start postgresql@17

# Verify installation
brew services list | grep postgresql
```

### Configure PostgreSQL Data Directory

```bash
# Check PostgreSQL status
brew services list

# Create a custom data directory (optional but recommended for production)
# Stop PostgreSQL first
brew services stop postgresql@17

# Initialize a new database cluster in a custom location
initdb /usr/local/var/postgresql@17/custom_data

# Edit the plist file to use custom data directory
# File location: ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist
# Modify the PGDATA environment variable

# Or use environment variables
export PGDATA=/usr/local/var/postgresql@17/custom_data
```

### Basic PostgreSQL Configuration

Create initial configuration file:

```bash
# Locate postgresql.conf
SHOW config_file;
# Typically: /usr/local/var/postgresql@17/postgresql.conf or /usr/local/var/postgresql@17/custom_data/postgresql.conf

# Edit postgresql.conf with basic settings
# Add these lines to postgresql.conf:
listen_addresses = 'localhost'  # For development; change for production
port = 5432
max_connections = 100
shared_buffers = 256MB  # Adjust based on available RAM
work_mem = 4MB
maintenance_work_mem = 64MB
wal_buffers = 16MB
checkpoint_segments = 32  # For PostgreSQL < 9.5; for 9.5+ use max_wal_size
```

## Section 2: pgvector Extension Installation

### Install pgvector using Homebrew

```bash
# Install pgvector formula
brew install pgvector

# Verify installation
ls $(brew --prefix)/Cellar/pgvector/
```

### Alternative: Build from Source

If you need the latest version or custom build:

```bash
# Ensure PostgreSQL development headers are available
brew install postgresql@17

# Clone pgvector repository
cd /tmp
git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
cd pgvector

# Build and install
export PG_CONFIG=/usr/local/opt/postgresql@17/bin/pg_config
make
make install

# Restart PostgreSQL to load the extension
brew services restart postgresql@17
```

## Section 3: Database Creation and Configuration

### Create the Bibliography Database

```bash
# Connect to PostgreSQL as superuser
psql postgres

# Create bibliography database
CREATE DATABASE bibliography_db
    WITH OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

# Grant permissions (create a dedicated user for the application)
CREATE USER bibliography_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE bibliography_db TO bibliography_user;

# Exit psql
\q
```

### Enable pgvector Extension

```bash
# Connect to bibliography database
psql -d bibliography_db

# Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

# Verify extension installation
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name = 'vector';

# Check version
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

### Run Database Schema Creation Script

```bash
# Import the bibliography schema
psql -d bibliography_db -f create_bibliography_db.sql

# Verify schema creation
psql -d bibliography_db -c "\dt"
psql -d bibliography_db -c "\di"
```

## Section 4: Verification and Testing

### Basic Connectivity Test

```bash
# Test database connection
psql -d bibliography_db -c "SELECT version();"

# Test pgvector functionality
psql -d bibliography_db -c "
CREATE TABLE test_vectors (
    id SERIAL PRIMARY KEY,
    embedding vector(384)
);

INSERT INTO test_vectors (embedding) VALUES ('[0.1,0.2,0.3,-0.1,-0.2,-0.3]');
INSERT INTO test_vectors (embedding) VALUES ('[0.2,0.3,0.4,-0.2,-0.3,-0.4]');

SELECT id, embedding <-> '[0.1,0.2,0.3,-0.1,-0.2,-0.3]' AS distance
FROM test_vectors
ORDER BY distance
LIMIT 5;

DROP TABLE test_vectors;
"
```

### Performance Verification

```bash
# Create test indexes
psql -d bibliography_db -c "
-- Test HNSW index creation
CREATE TABLE test_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(384)
);

-- Insert test data
INSERT INTO test_embeddings (content, embedding)
SELECT
    'Document ' || i,
    ('[' || string_agg((random() * 2 - 1)::text, ',') || ']')::vector
FROM generate_series(1, 1000) i,
     generate_series(1, 384) j
GROUP BY i;

-- Create vector index
CREATE INDEX ON test_embeddings USING hnsw (embedding vector_cosine_ops);

-- Test similarity search
SELECT id, content,
       1 - (embedding <=> '[0.1,0.2,0.3]') AS similarity
FROM test_embeddings
ORDER BY similarity DESC
LIMIT 10;

DROP TABLE test_embeddings;
"
```

## Section 5: Security Considerations for Production

### User Authentication and Authorization

```bash
# Create application user with limited privileges
psql -d bibliography_db -c "
-- Create application role
CREATE ROLE bibliography_app WITH LOGIN PASSWORD 'secure_app_password';
GRANT CONNECT ON DATABASE bibliography_db TO bibliography_app;

-- Grant specific schema permissions
GRANT USAGE ON SCHEMA public TO bibliography_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bibliography_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO bibliography_app;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bibliography_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO bibliography_app;
"

# Configure pg_hba.conf for secure authentication
# Edit /usr/local/var/postgresql@17/pg_hba.conf
# Add entries like:
# local   bibliography_db   bibliography_app   scram-sha-256
# host    bibliography_db   bibliography_app   127.0.0.1/32   scram-sha-256
```

### Data Encryption

```bash
# Enable SSL/TLS connections
# Edit postgresql.conf
ssl = on
ssl_cert_file = '/usr/local/var/postgresql@17/server.crt'
ssl_key_file = '/usr/local/var/postgresql@17/server.key'

# Generate self-signed certificate (for development/testing only)
openssl req -new -x509 -days 365 -nodes -text -out server.crt -keyout server.key -subj "/CN=localhost"

# Set proper permissions
chmod 600 server.key
chown postgres:postgres server.crt server.key

# For production, obtain proper SSL certificates from a trusted CA
```

### Network Security

```bash
# Configure firewall rules (using pf or Little Snitch)
# Allow only local connections for development
# Edit postgresql.conf
listen_addresses = 'localhost'

# For production with remote access:
listen_addresses = '192.168.1.100'  # Specific IP
# Or use a reverse proxy like nginx for additional security
```

### Audit Logging

```bash
# Enable audit logging
# Edit postgresql.conf
log_statement = 'ddl'  # Log DDL statements
log_statement = 'mod'  # Log data modification statements
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_connections = on
log_disconnections = on

# Restart PostgreSQL
brew services restart postgresql@17
```

## Section 6: Performance Tuning

### Memory Configuration

```bash
# Edit postgresql.conf for production workloads
# Adjust based on available RAM (assuming 16GB system)

# Memory settings
shared_buffers = 4GB  # 25% of total RAM
effective_cache_size = 12GB  # 75% of total RAM
work_mem = 8MB  # Per connection; adjust based on max_connections
maintenance_work_mem = 512MB  # For index creation/vacuum

# Parallel processing
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_parallel_maintenance_workers = 4

# WAL settings
wal_level = replica
max_wal_size = 2GB
min_wal_size = 80MB
```

### pgvector-Specific Tuning

```bash
# Connect to database and set pgvector parameters
psql -d bibliography_db -c "
-- Set default search parameters for better recall
ALTER SYSTEM SET hnsw.ef_search = 100;
ALTER SYSTEM SET ivfflat.probes = 10;

-- For production, adjust based on your specific use case
-- Higher ef_search = better recall but slower queries
-- Higher probes = better recall but slower queries
"

# Restart PostgreSQL to apply system-level changes
brew services restart postgresql@17
```

### Index Optimization

```bash
# Build indexes with optimized settings
psql -d bibliography_db -c "
-- Set maintenance memory for index creation
SET maintenance_work_mem = '1GB';
SET max_parallel_maintenance_workers = 4;

-- Create vector indexes (already done in schema, but for reference)
CREATE INDEX CONCURRENTLY ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX CONCURRENTLY ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create additional performance indexes
CREATE INDEX CONCURRENTLY ON documents (document_type, created_at);
CREATE INDEX CONCURRENTLY ON scientific_papers (publication_year, journal);
"
```

## Section 7: Backup and Recovery

### Automated Backup Setup

```bash
# Create backup directory
sudo mkdir -p /usr/local/var/postgresql@17/backups
sudo chown postgres:postgres /usr/local/var/postgresql@17/backups

# Create backup script
cat > /usr/local/var/postgresql@17/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/usr/local/var/postgresql@17/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/bibliography_db_$TIMESTAMP.sql"

# Create backup
pg_dump -U postgres -d bibliography_db -f "$BACKUP_FILE" --no-password

# Compress backup
gzip "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF

chmod +x /usr/local/var/postgresql@17/backup.sh

# Setup daily cron job
(crontab -l ; echo "0 2 * * * /usr/local/var/postgresql@17/backup.sh") | crontab -
```

### Manual Backup and Restore

```bash
# Manual backup
pg_dump -U postgres -d bibliography_db -f bibliography_backup.sql

# Backup with compression
pg_dump -U postgres -d bibliography_db | gzip > bibliography_backup.sql.gz

# Restore from backup
createdb -U postgres bibliography_db_restored
psql -U postgres -d bibliography_db_restored -f bibliography_backup.sql

# Or restore compressed backup
gunzip -c bibliography_backup.sql.gz | psql -U postgres -d bibliography_db_restored
```

## Section 8: Troubleshooting

### Common Issues

#### PostgreSQL Won't Start

```bash
# Check PostgreSQL logs
tail -f /usr/local/var/log/postgresql@17.log

# Check if port 5432 is already in use
lsof -i :5432

# Kill conflicting process or change port in postgresql.conf
```

#### pgvector Extension Not Found

```bash
# Check if extension is installed
psql -d bibliography_db -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"

# Reinstall pgvector
brew reinstall pgvector
brew services restart postgresql@17

# Verify PG_CONFIG path
which pg_config
pg_config --version
```

#### Performance Issues

```bash
# Analyze slow queries
psql -d bibliography_db -c "
SELECT query, calls, ROUND((total_plan_time + total_exec_time) / calls) AS avg_time_ms
FROM pg_stat_statements
ORDER BY total_plan_time + total_exec_time DESC
LIMIT 10;
"

# Reset statistics
psql -d bibliography_db -c "SELECT pg_stat_statements_reset();"

# Analyze specific query
EXPLAIN ANALYZE SELECT * FROM documents ORDER BY embedding <-> '[0.1,0.2,0.3]' LIMIT 5;
```

#### Memory Issues

```bash
# Check current memory usage
psql -d bibliography_db -c "SHOW shared_buffers; SHOW work_mem; SHOW maintenance_work_mem;"

# Monitor system memory
vm_stat
```

### Diagnostic Commands

```bash
# Check PostgreSQL status
brew services list | grep postgresql

# View PostgreSQL logs
tail -f /usr/local/var/log/postgresql@17.log

# Check database size
psql -d bibliography_db -c "SELECT pg_size_pretty(pg_database_size('bibliography_db'));"

# Check table sizes
psql -d bibliography_db -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Check running queries
psql -d bibliography_db -c "SELECT pid, query, state, now() - query_start AS duration FROM pg_stat_activity WHERE state = 'active';"
```

## Section 9: Maintenance Procedures

### Regular Maintenance Tasks

```bash
# Vacuum and analyze database
psql -d bibliography_db -c "VACUUM ANALYZE;"

# Reindex database (run during low usage periods)
psql -d bibliography_db -c "REINDEX DATABASE bibliography_db;"

# Update statistics
psql -d bibliography_db -c "ANALYZE;"
```

### Monitoring Setup

```bash
# Enable pg_stat_statements for query monitoring
psql -d bibliography_db -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Basic monitoring queries
psql -d bibliography_db -c "
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check database size
SELECT pg_size_pretty(pg_database_size('bibliography_db'));

-- Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename) DESC
LIMIT 10;
"
```

## Appendix: Configuration Reference

### postgresql.conf Key Settings

```ini
# Connection Settings
listen_addresses = 'localhost'
port = 5432
max_connections = 100

# Memory Settings
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 8MB
maintenance_work_mem = 512MB

# Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 2GB

# Logging
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'ddl'
log_connections = on
log_disconnections = on

# Performance
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Environment Variables

```bash
# Set in ~/.zshrc or ~/.bash_profile
export PGHOST=localhost
export PGPORT=5432
export PGUSER=bibliography_user
export PGDATABASE=bibliography_db
export PGPASSWORD=secure_password_here
```

---

This guide provides a complete PostgreSQL and pgvector setup for the bibliography project. For production deployments, consult with a database administrator and perform thorough security audits before going live.
