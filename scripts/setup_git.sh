#!/bin/bash

# HERO Evidence Library - v2 Git Setup Script
# This script configures the v2 repository to sync with v1

set -e  # Exit on error

echo "🚀 HERO Evidence Library v2 - Git Configuration"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
V1_PATH="/Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library"
V2_PATH="/Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2"

echo -e "${BLUE}Step 1: Checking v1 repository${NC}"
cd "$V1_PATH"
echo "  Current branch: $(git branch --show-current)"
echo "  Latest commit: $(git log -1 --oneline)"
echo ""

echo -e "${BLUE}Step 2: Setting up v2 repository${NC}"
cd "$V2_PATH"

# Check if v2-podcast-generation branch exists
if git show-ref --verify --quiet refs/heads/feature/v2-podcast-generation; then
    echo -e "${YELLOW}  Branch 'feature/v2-podcast-generation' already exists${NC}"
    git checkout feature/v2-podcast-generation
else
    echo "  Creating branch 'feature/v2-podcast-generation'"
    git checkout -b feature/v2-podcast-generation
fi

echo ""
echo -e "${BLUE}Step 3: Adding v1 as upstream remote${NC}"

# Check if remote already exists
if git remote | grep -q "v1-upstream"; then
    echo -e "${YELLOW}  Remote 'v1-upstream' already exists${NC}"
    # Update the URL in case it changed
    git remote set-url v1-upstream "$V1_PATH"
else
    echo "  Adding v1-upstream remote"
    git remote add v1-upstream "$V1_PATH"
fi

echo ""
echo -e "${BLUE}Step 4: Verifying configuration${NC}"
echo "  Remotes:"
git remote -v | sed 's/^/    /'

echo ""
echo "  Branches:"
git branch -a | sed 's/^/    /'

echo ""
echo -e "${BLUE}Step 5: Initial sync from v1${NC}"
echo "  Fetching from v1-upstream..."
git fetch v1-upstream main

echo ""
echo "  Current status:"
git status

echo ""
echo -e "${GREEN}✅ Git configuration complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review any uncommitted changes: git status"
echo "  2. Commit v2 foundation files: git add . && git commit -m 'Initial v2 setup'"
echo "  3. Merge v1 updates: git merge v1-upstream/main"
echo ""
echo "For daily workflow, see: docs/GIT_WORKFLOW_GUIDE.md"
echo ""
