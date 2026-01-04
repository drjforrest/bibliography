#!/bin/bash

# HERO Evidence Library - Daily Sync Script
# Keeps v2 updated with v1 changes

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Paths
V1_PATH="/Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library"
V2_PATH="/Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2"

echo -e "${BLUE}📦 HERO Evidence Library - Daily Sync${NC}"
echo "========================================"
echo ""

# Function to check for uncommitted changes
check_uncommitted() {
    if [[ -n $(git status -s) ]]; then
        echo -e "${YELLOW}⚠️  Warning: Uncommitted changes detected${NC}"
        echo ""
        git status -s
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted. Please commit or stash changes first."
            exit 1
        fi
    fi
}

# Step 1: Update v1 from GitHub (if applicable)
echo -e "${BLUE}Step 1: Updating v1 from GitHub${NC}"
cd "$V1_PATH"
check_uncommitted

CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "  Switching to main branch..."
    git checkout main
fi

echo "  Pulling latest changes..."
git pull origin main
echo -e "${GREEN}  ✅ v1 updated${NC}"
echo ""

# Step 2: Update v2 from GitHub
echo -e "${BLUE}Step 2: Updating v2 from GitHub${NC}"
cd "$V2_PATH"
check_uncommitted

CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "feature/v2-podcast-generation" ]; then
    echo "  Switching to feature/v2-podcast-generation branch..."
    git checkout feature/v2-podcast-generation
fi

echo "  Pulling latest changes..."
git pull origin feature/v2-podcast-generation 2>/dev/null || echo "  (No remote branch yet)"
echo -e "${GREEN}  ✅ v2 updated${NC}"
echo ""

# Step 3: Fetch v1 updates
echo -e "${BLUE}Step 3: Fetching v1 updates${NC}"
git fetch v1-upstream main
echo -e "${GREEN}  ✅ Fetched${NC}"
echo ""

# Step 4: Check if merge is needed
MERGE_BASE=$(git merge-base HEAD v1-upstream/main)
V1_HEAD=$(git rev-parse v1-upstream/main)

if [ "$MERGE_BASE" == "$V1_HEAD" ]; then
    echo -e "${GREEN}✨ v2 is already up to date with v1${NC}"
    echo ""
    echo "Summary:"
    echo "  v1 status: $(cd "$V1_PATH" && git log -1 --oneline)"
    echo "  v2 status: $(git log -1 --oneline)"
else
    echo -e "${BLUE}Step 4: Merging v1 changes into v2${NC}"
    
    # Show what will be merged
    echo "  Changes from v1:"
    git log --oneline HEAD..v1-upstream/main | sed 's/^/    /'
    echo ""
    
    # Attempt merge
    echo "  Merging..."
    if git merge v1-upstream/main -m "Merge v1 updates into v2"; then
        echo -e "${GREEN}  ✅ Merge successful${NC}"
        
        # Push if no conflicts
        echo ""
        read -p "Push to GitHub? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            git push origin feature/v2-podcast-generation
            echo -e "${GREEN}  ✅ Pushed to GitHub${NC}"
        fi
    else
        echo -e "${RED}  ⚠️  Merge conflicts detected${NC}"
        echo ""
        echo "  Files with conflicts:"
        git status -s | grep "^UU" | sed 's/^/    /'
        echo ""
        echo "  To resolve:"
        echo "    1. Edit conflicting files"
        echo "    2. git add <resolved-files>"
        echo "    3. git commit"
        echo "    4. git push origin feature/v2-podcast-generation"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎉 Sync complete!${NC}"
echo ""
echo "Current state:"
echo "  v1 (main): $(cd "$V1_PATH" && git log -1 --oneline)"
echo "  v2 (v2-podcast-generation): $(git log -1 --oneline)"
echo ""
