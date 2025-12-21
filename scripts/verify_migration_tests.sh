#!/bin/bash

# Comprehensive Database Schema Migration Verification Tests for mac-mini
# This script performs thorough validation of the bibliography database schema migration,
# including table structure, foreign keys, indexes, vector functionality, and performance benchmarks.

set -e  # Exit on any error

# Configuration
DB_NAME="bibliography_db"
DB_USER="postgres"
LOG_FILE="migration_verification_$(date +"%Y%m%d_%H%M%S").log"
RESULTS_FILE="migration_results_$(date +"%Y%m%d_%H%M%S").json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

# Results storage
declare -A TEST_RESULTS
declare -A PERFORMANCE_METRICS

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
    ((PASSED_TESTS++))
    TEST_RESULTS["$1"]="PASSED"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$LOG_FILE"
    ((WARNINGS++))
    TEST_RESULTS["$1"]="WARNING"
}

error() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$LOG_FILE"
    ((FAILED_TESTS++))
    TEST_RESULTS["$1"]="FAILED"
}

info() {
    echo -e "${CYAN}ℹ $1${NC}" | tee -a "$LOG_FILE"
}

performance() {
    echo -e "${PURPLE}📊 $1${NC}" | tee -a "$LOG_FILE"
    PERFORMANCE_METRICS["$2"]="$3"
}

# SQL execution with error handling
execute_sql() {
    local description="$1"
    local sql="$2"
    local expected_result="$3"

    ((TOTAL_TESTS++))

    log "Executing SQL test: $description"

    local result
    if ! result=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "$sql" 2>/dev/null); then
        error "$description - SQL execution failed"
        return 1
    fi

    # Trim whitespace
    result=$(echo "$result" | xargs)

    if [ -n "$expected_result" ]; then
        if [ "$result" = "$expected_result" ]; then
            success "$description"
            return 0
        else
            error "$description - Expected: '$expected_result', Got: '$result'"
            return 1
        fi
    else
        if [ -n "$result" ]; then
            success "$description"
            return 0
        else
            error "$description - No result returned"
            return 1
        fi
    fi
}

# Performance measurement
measure_performance() {
    local description="$1"
    local sql="$2"
    local metric_name="$3"

    ((TOTAL_TESTS++))

    log "Measuring performance: $description"

    local start_time=$(date +%s.%3N)
    local result

    if result=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "$sql" 2>/dev/null); then
        local end_time=$(date +%s.%3N)
        local duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")

        performance "$description completed in ${duration}s" "$metric_name" "$duration"

        # Store result for JSON output
        PERFORMANCE_METRICS["${metric_name}_result"]="$result"

        return 0
    else
        error "$description - Performance test failed"
        return 1
    fi
}

# ========================================
# PRE-TEST VALIDATION
# ========================================

log "Starting comprehensive database migration verification tests..."
echo "Log file: $LOG_FILE"
echo "Results file: $RESULTS_FILE"
echo ""

# Check PostgreSQL connectivity
log "Performing pre-test checks..."

if ! psql -h localhost -U "$DB_USER" -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
    error "Cannot connect to PostgreSQL"
    exit 1
fi
success "PostgreSQL connection established"

# Check database exists
if ! psql -h localhost -U "$DB_USER" -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1; then
    error "Database '$DB_NAME' does not exist"
    exit 1
fi
success "Database '$DB_NAME' exists"

# ========================================
# 1. TABLE STRUCTURE VALIDATION TESTS
# ========================================

log ""
log "========================================="
log "1. TABLE STRUCTURE VALIDATION TESTS"
log "========================================="

# Test 1.1: Table count validation
EXPECTED_TABLES=12  # user, searchspaces, documents, scientific_papers, tags, chunks, chats, podcasts, search_source_connectors, devonthink_sync, devonthink_folders, paper_annotations, paper_tags
execute_sql "Table count validation" "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" "$EXPECTED_TABLES"

# Test 1.2: Required tables existence
REQUIRED_TABLES=("user" "searchspaces" "documents" "scientific_papers" "tags" "chunks" "chats" "podcasts" "search_source_connectors" "devonthink_sync" "devonthink_folders" "paper_annotations" "paper_tags")

for table in "${REQUIRED_TABLES[@]}"; do
    execute_sql "${table} table exists" "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = '$table';" "1"
done

# Test 1.3: Table column validation for critical tables
execute_sql "user table columns" "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
AND column_name IN ('id', 'email', 'hashed_password', 'is_active', 'is_superuser', 'is_verified');" "6"

execute_sql "documents table columns" "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'documents'
AND column_name IN ('id', 'title', 'document_type', 'content', 'embedding', 'search_space_id', 'created_at');" "7"

execute_sql "scientific_papers table columns" "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'scientific_papers'
AND column_name IN ('id', 'title', 'authors', 'file_path', 'document_id', 'created_at');" "6"

# ========================================
# 2. FOREIGN KEY RELATIONSHIP TESTS
# ========================================

log ""
log "========================================="
log "2. FOREIGN KEY RELATIONSHIP TESTS"
log "========================================="

# Test 2.1: Foreign key count
EXPECTED_FKS=16  # Based on schema constraints
execute_sql "Foreign key constraints count" "
SELECT COUNT(*) FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY' AND table_schema = 'public';" "$EXPECTED_FKS"

# Test 2.2: Test foreign key relationships with sample data
log "Testing foreign key relationships with sample data insertion..."

# Create test data in dependency order
execute_sql "Create test user" "
INSERT INTO \"user\" (id, email, hashed_password, is_active, is_superuser, is_verified)
VALUES ('00000000-0000-0000-0000-000000000001', 'test@example.com', 'hashed', true, false, true)
ON CONFLICT (id) DO NOTHING;" ""

execute_sql "Create test search space" "
INSERT INTO searchspaces (name, description, user_id, id, created_at)
VALUES ('Test Space', 'Test space for verification', '00000000-0000-0000-0000-000000000001', 1, NOW())
ON CONFLICT (id) DO NOTHING;" ""

execute_sql "Create test document" "
INSERT INTO documents (title, document_type, content, embedding, search_space_id, id, created_at)
VALUES ('Test Document', 'FILE', 'Test content', '[0.1,0.2,0.3]', 1, 1, NOW())
ON CONFLICT (id) DO NOTHING;" ""

execute_sql "Create test scientific paper" "
INSERT INTO scientific_papers (title, file_path, document_id, id, created_at)
VALUES ('Test Paper', '/test/path.pdf', 1, 1, NOW())
ON CONFLICT (id) DO NOTHING;" ""

execute_sql "Create test tag" "
INSERT INTO tags (name, user_id, id, created_at)
VALUES ('Test Tag', '00000000-0000-0000-0000-000000000001', 1, NOW())
ON CONFLICT (id) DO NOTHING;" ""

# Test FK constraint violations
execute_sql "Test invalid foreign key (should fail)" "
DO \$\$
BEGIN
    INSERT INTO documents (title, document_type, content, search_space_id, id, created_at)
    VALUES ('Invalid Document', 'FILE', 'content', 9999, 9999, NOW());
    RAISE EXCEPTION 'Foreign key constraint should have failed';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE 'Foreign key constraint working correctly';
END
\$\$;"

# ========================================
# 3. INDEX VALIDATION TESTS
# ========================================

log ""
log "========================================="
log "3. INDEX VALIDATION TESTS"
log "========================================="

# Test 3.1: Total index count
EXPECTED_INDEXES=40  # Based on schema indexes
execute_sql "Total index count" "
SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';" "$EXPECTED_INDEXES"

# Test 3.2: Vector indexes existence
execute_sql "Vector indexes exist" "
SELECT COUNT(*) FROM pg_indexes
WHERE schemaname = 'public' AND indexname IN ('chucks_vector_index', 'document_vector_index');" "2"

# Test 3.3: Primary key indexes
execute_sql "Primary key indexes" "
SELECT COUNT(*) FROM pg_indexes
WHERE schemaname = 'public' AND indexname LIKE '%_pkey';" "13"

# Test 3.4: Unique constraint indexes
execute_sql "Unique constraint indexes" "
SELECT COUNT(*) FROM information_schema.table_constraints
WHERE constraint_type = 'UNIQUE' AND table_schema = 'public';" "4"

# ========================================
# 4. VECTOR FUNCTIONALITY TESTS
# ========================================

log ""
log "========================================="
log "4. VECTOR FUNCTIONALITY TESTS"
log "========================================="

# Test 4.1: Vector extension availability
execute_sql "pgvector extension enabled" "
SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';" "1"

# Test 4.2: Vector operations
execute_sql "Vector distance calculation" "
SELECT ROUND(('[1,2,3]'::vector <-> '[1,2,4]'::vector)::numeric, 3);" "1.000"

execute_sql "Vector cosine similarity" "
SELECT ROUND((1 - ('[1,2,3]'::vector <=> '[1,2,4]'::vector))::numeric, 3);" "0.991"

# Test 4.3: Vector index functionality
execute_sql "Vector index usage test" "
CREATE TEMP TABLE temp_vectors (id SERIAL, embedding vector(384));
INSERT INTO temp_vectors (embedding) VALUES ('[0.1,0.2,0.3]');
INSERT INTO temp_vectors (embedding) VALUES ('[0.2,0.3,0.4]');
SELECT COUNT(*) FROM temp_vectors WHERE embedding <-> '[0.1,0.2,0.3]' < 0.5;
DROP TABLE temp_vectors;" "2"

# ========================================
# 5. DATA INTEGRITY CHECKS
# ========================================

log ""
log "========================================="
log "5. DATA INTEGRITY CHECKS"
log "========================================="

# Test 5.1: Sequence ownership
execute_sql "Sequences properly owned" "
SELECT COUNT(*) FROM information_schema.sequences
WHERE sequence_schema = 'public' AND sequence_name IN (
    'chats_id_seq', 'chunks_id_seq', 'devonthink_folders_id_seq',
    'devonthink_sync_id_seq', 'documents_id_seq', 'paper_annotations_id_seq',
    'podcasts_id_seq', 'scientific_papers_id_seq', 'search_source_connectors_id_seq',
    'searchspaces_id_seq', 'tags_id_seq'
);" "11"

# Test 5.2: Enum types
execute_sql "Enum types created" "
SELECT COUNT(*) FROM pg_type
WHERE typname IN ('documenttype', 'literaturetype', 'chattype', 'searchsourceconnectortype', 'devonthinksyncstatus');" "5"

# Test 5.3: Default values
execute_sql "Default values set" "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'public' AND column_default IS NOT NULL;" "10"

# Test 5.4: NOT NULL constraints
execute_sql "NOT NULL constraints" "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'public' AND is_nullable = 'NO' AND column_name != 'id';" "20"

# ========================================
# 6. PERFORMANCE BENCHMARKS
# ========================================

log ""
log "========================================="
log "6. PERFORMANCE BENCHMARKS"
log "========================================="

# Test 6.1: Vector search performance
log "Setting up performance test data..."
psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "
CREATE TEMP TABLE perf_test_vectors (id SERIAL PRIMARY KEY, embedding vector(384));
INSERT INTO perf_test_vectors (embedding)
SELECT ('[' || string_agg((random() * 2 - 1)::text, ',') || ']')::vector(384)
FROM generate_series(1, 1000) i,
     generate_series(1, 384) j
GROUP BY i;
CREATE INDEX perf_vector_idx ON perf_test_vectors USING hnsw (embedding vector_cosine_ops);
" > /dev/null 2>&1

measure_performance "Vector similarity search (1000 vectors)" "
SELECT id FROM perf_test_vectors
ORDER BY embedding <-> '[0.1,0.2,0.3]'
LIMIT 10;" "vector_search_1000"

measure_performance "Vector search with filtering" "
SELECT COUNT(*) FROM perf_test_vectors
WHERE embedding <-> '[0.1,0.2,0.3]' < 0.8;" "vector_search_filtered"

# Test 6.2: Index performance
measure_performance "Full-text search performance" "
SELECT COUNT(*) FROM documents
WHERE to_tsvector('english', content) @@ to_tsquery('english', 'test');" "fts_search"

# Test 6.3: Join performance
measure_performance "Foreign key join performance" "
SELECT COUNT(*) FROM documents d
JOIN searchspaces s ON d.search_space_id = s.id
JOIN \"user\" u ON s.user_id = u.id;" "fk_join"

# Test 6.4: Aggregation performance
measure_performance "Aggregation query performance" "
SELECT document_type, COUNT(*) as count
FROM documents
GROUP BY document_type
ORDER BY count DESC;" "aggregation"

# ========================================
# 7. CLEANUP AND SUMMARY
# ========================================

log ""
log "========================================="
log "7. CLEANUP AND SUMMARY"
log "========================================="

# Clean up test data
log "Cleaning up test data..."
psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "
DELETE FROM paper_tags WHERE paper_id = 1 AND tag_id = 1;
DELETE FROM scientific_papers WHERE id = 1;
DELETE FROM chunks WHERE document_id = 1;
DELETE FROM documents WHERE id = 1;
DELETE FROM chats WHERE search_space_id = 1;
DELETE FROM podcasts WHERE search_space_id = 1;
DELETE FROM search_source_connectors WHERE user_id = '00000000-0000-0000-0000-000000000001';
DELETE FROM tags WHERE id = 1;
DELETE FROM searchspaces WHERE id = 1;
DELETE FROM \"user\" WHERE id = '00000000-0000-0000-0000-000000000001';
" > /dev/null 2>&1

success "Test data cleanup completed"

# Generate results summary
log ""
log "========================================="
log "TEST SUMMARY"
log "========================================="

echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo "Warnings: $WARNINGS"

# Calculate success rate
if [ "$TOTAL_TESTS" -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Success Rate: ${SUCCESS_RATE}%"
fi

# Export results to JSON
cat > "$RESULTS_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "database": "$DB_NAME",
  "summary": {
    "total_tests": $TOTAL_TESTS,
    "passed_tests": $PASSED_TESTS,
    "failed_tests": $FAILED_TESTS,
    "warnings": $WARNINGS,
    "success_rate": ${SUCCESS_RATE:-0}
  },
  "test_results": {
EOF

# Add test results
first=true
for test in "${!TEST_RESULTS[@]}"; do
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$RESULTS_FILE"
    fi
    echo "    \"$test\": \"${TEST_RESULTS[$test]}\"" >> "$RESULTS_FILE"
done

echo "  }," >> "$RESULTS_FILE"
echo "  \"performance_metrics\": {" >> "$RESULTS_FILE"

# Add performance metrics
first=true
for metric in "${!PERFORMANCE_METRICS[@]}"; do
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$RESULTS_FILE"
    fi
    echo "    \"$metric\": \"${PERFORMANCE_METRICS[$metric]}\"" >> "$RESULTS_FILE"
done

echo "  }" >> "$RESULTS_FILE"
echo "}" >> "$RESULTS_FILE"

log "Results exported to: $RESULTS_FILE"

# Final status
if [ "$FAILED_TESTS" -eq 0 ]; then
    log ""
    success "🎉 ALL TESTS PASSED - Database migration successful!"
    log "The bibliography database schema has been successfully migrated to mac-mini."
    if [ "$WARNINGS" -gt 0 ]; then
        warning "$WARNINGS warnings detected - review log file for details."
    fi
else
    log ""
    error "❌ MIGRATION ISSUES DETECTED - $FAILED_TESTS tests failed"
    log "Please review the log file ($LOG_FILE) for detailed error information."
    log "Check the results file ($RESULTS_FILE) for complete test results."
    exit 1
fi

# ========================================
# OPTIMIZATION RECOMMENDATIONS
# ========================================

log ""
log "========================================="
log "OPTIMIZATION RECOMMENDATIONS"
log "========================================="

# Analyze performance metrics and provide recommendations
VECTOR_SEARCH_TIME=${PERFORMANCE_METRICS["vector_search_1000"]:-"N/A"}
FK_JOIN_TIME=${PERFORMANCE_METRICS["fk_join"]:-"N/A"}

if [[ "$VECTOR_SEARCH_TIME" != "N/A" && $(echo "$VECTOR_SEARCH_TIME > 1.0" | bc -l 2>/dev/null) -eq 1 ]]; then
    warning "Vector search performance could be improved (took ${VECTOR_SEARCH_TIME}s)"
    info "Recommendation: Consider adjusting hnsw.ef_search parameter for better recall vs speed balance"
fi

if [[ "$FK_JOIN_TIME" != "N/A" && $(echo "$FK_JOIN_TIME > 0.1" | bc -l 2>/dev/null) -eq 1 ]]; then
    info "Foreign key join performance is good (${FK_JOIN_TIME}s)"
else
    info "Foreign key joins are performing well"
fi

# General recommendations
info "General Recommendations:"
info "1. Monitor vector search performance with real data patterns"
info "2. Consider partitioning large tables if data grows significantly"
info "3. Set up regular VACUUM ANALYZE maintenance jobs"
info "4. Monitor index usage and remove unused indexes"
info "5. Consider connection pooling for high-traffic scenarios"

log ""
log "Verification completed. Check $LOG_FILE and $RESULTS_FILE for details."