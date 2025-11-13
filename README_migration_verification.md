# Database Migration Verification Guide

This document provides comprehensive guidance for validating the bibliography database schema migration success on the mac-mini deployment.

## Overview

The `verify_migration_tests.sh` script performs thorough validation of the migrated database, including:

- Table structure validation
- Foreign key relationship verification
- Index functionality testing
- Vector operations validation
- Data integrity checks
- Performance benchmarking
- Comprehensive logging and reporting

## Prerequisites

1. PostgreSQL 17+ running on mac-mini
2. pgvector extension installed and enabled
3. Bibliography database created and schema imported
4. Execute permissions on the verification script

## Usage

### 1. Make Script Executable

```bash
chmod +x verify_migration_tests.sh
```

### 2. Run Verification Tests

```bash
./verify_migration_tests.sh
```

### 3. Review Results

The script generates two output files:

- `migration_verification_YYYYMMDD_HHMMSS.log` - Detailed execution log
- `migration_results_YYYYMMDD_HHMMSS.json` - Structured test results

## Test Categories

### 1. Table Structure Validation

- Verifies all required tables exist (13 tables)
- Validates column definitions for critical tables
- Checks table creation order and dependencies

### 2. Foreign Key Relationships

- Tests foreign key constraint creation (16 constraints)
- Validates referential integrity with sample data
- Ensures cascade delete behavior works correctly

### 3. Index Validation

- Verifies vector indexes (HNSW) for semantic search
- Checks full-text search indexes (GIN)
- Validates B-tree indexes for standard queries
- Confirms primary key and unique constraint indexes

### 4. Vector Functionality

- Tests pgvector extension availability
- Validates vector distance calculations (L2, cosine)
- Ensures vector indexes work correctly
- Performance tests for vector operations

### 5. Data Integrity

- Validates sequence ownership and auto-increment
- Checks enum types and default values
- Verifies NOT NULL constraints
- Tests data type consistency

### 6. Performance Benchmarks

- Vector similarity search performance
- Full-text search speed
- Foreign key join performance
- Aggregation query efficiency

## Expected Results

A successful migration should show:

- ✅ All 13 required tables present
- ✅ 16 foreign key constraints active
- ✅ 40+ indexes created
- ✅ pgvector extension enabled
- ✅ Vector operations functional
- ✅ All data integrity constraints valid
- ✅ Performance benchmarks within acceptable ranges

## Troubleshooting

### Common Issues

#### PostgreSQL Connection Failed

```
Error: Cannot connect to PostgreSQL
```

**Solution:**

- Verify PostgreSQL service is running: `brew services list`
- Check connection: `psql -h localhost -U postgres -d postgres`
- Review PostgreSQL logs: `tail -f /usr/local/var/log/postgresql@17.log`

#### Database Not Found

```
Error: Database 'bibliography_db' does not exist
```

**Solution:**

- Create database: `createdb -U postgres bibliography_db`
- Run schema import: `./import_bibliography_schema.sh`

#### pgvector Extension Missing

```
Error: pgvector extension not available
```

**Solution:**

- Install pgvector: `brew install pgvector`
- Restart PostgreSQL: `brew services restart postgresql@17`
- Enable extension: `psql -d bibliography_db -c "CREATE EXTENSION vector;"`

#### Test Failures

Review the detailed log file for specific error messages and failed tests.

## Performance Optimization Recommendations

Based on test results, the script provides tailored recommendations:

### Vector Search Optimization

- Adjust `hnsw.ef_search` parameter (default: 64, increase for better recall)
- Consider `ivfflat.probes` for IVF indexes (default: 10)
- Monitor query latency vs. accuracy trade-offs

### Index Maintenance

- Regular `VACUUM ANALYZE` for statistics updates
- Monitor index usage with `pg_stat_user_indexes`
- Consider `REINDEX CONCURRENTLY` for large indexes

### Memory Configuration

- Adjust `maintenance_work_mem` for index creation
- Monitor `work_mem` for complex queries
- Consider `shared_buffers` based on available RAM

### Query Optimization

- Use `EXPLAIN ANALYZE` for slow queries
- Consider partial indexes for filtered queries
- Implement query result caching if needed

## Monitoring and Maintenance

### Regular Health Checks

Run verification tests periodically to ensure:

- Schema integrity remains intact
- Performance benchmarks stay within acceptable ranges
- No unexpected changes to table structures

### Alert Thresholds

Consider implementing alerts for:

- Test failure rate > 5%
- Vector search latency > 500ms
- Foreign key constraint violations

## Integration Testing

After successful schema verification, perform:

1. Application connectivity tests
2. CRUD operation validation
3. Vector search functionality testing
4. Data migration verification (if applicable)

## Support

For issues with the verification script:

1. Check the detailed log file for error messages
2. Review PostgreSQL logs for underlying issues
3. Validate environment setup against prerequisites
4. Run individual test sections for isolation

## Test Output Example

```
=========================================
TEST SUMMARY
=========================================
Total Tests: 25
Passed: 23
Failed: 2
Warnings: 0
Success Rate: 92%

🎉 MIGRATION MOSTLY SUCCESSFUL
2 issues detected - review log file for details.
```

## JSON Results Format

```json
{
  "timestamp": "2025-11-13T01:20:48-08:00",
  "database": "bibliography_db",
  "summary": {
    "total_tests": 25,
    "passed_tests": 23,
    "failed_tests": 2,
    "warnings": 0,
    "success_rate": 92
  },
  "test_results": {
    "Table count validation": "PASSED",
    "Foreign key constraints count": "PASSED"
  },
  "performance_metrics": {
    "vector_search_1000": "0.234",
    "fk_join": "0.045"
  }
}
```

This verification suite ensures your bibliography database migration is robust, performant, and ready for production use on the mac-mini.
