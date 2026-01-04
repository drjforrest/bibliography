# Git Workflow Guide - v1 + v2 Development Strategy

## Overview

You have two repositories that need to stay synchronized:
- **v1 (production)**: `/Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/`
- **v2 (development)**: `/Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/`

This guide provides the complete workflow for keeping v1 updated while developing v2.

---

## Initial Git Setup

### Step 1: Check Current Git Status

```bash
# Check v1 repository
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git status
git remote -v
git branch

# Check v2 repository
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git status
git remote -v
git branch
```

### Step 2: Set Up v2 Repository Properly

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Create and switch to v2 development branch
git checkout -b feature/v2-podcast-generation

# Verify you're on the new branch
git branch
# Should show: * feature/v2-podcast-generation
```

### Step 3: Add v1 as an Upstream Remote (for pulling updates)

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Add v1 as a remote called 'v1-upstream'
git remote add v1-upstream /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library

# Verify remotes
git remote -v
# Should show:
# origin    <your-github-url> (fetch)
# origin    <your-github-url> (push)
# v1-upstream    /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library (fetch)
# v1-upstream    /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library (push)
```

---

## Daily Workflow

### Scenario 1: Continue v2 Development (Most Common)

```bash
# Work on v2
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Make sure you're on v2 branch
git checkout feature/v2-podcast-generation

# Make changes to files
# ... edit code ...

# Stage and commit changes
git add .
git commit -m "Add podcast generation nodes.py"

# Push to GitHub (optional, for backup)
git push origin feature/v2-podcast-generation
```

### Scenario 2: Update v1 Production Code

```bash
# Work on v1
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library

# Make sure you're on main branch
git checkout main

# Make changes
# ... fix bug, update feature ...

# Stage and commit
git add .
git commit -m "Fix: Resolve thumbnail loading issue"

# Push to GitHub
git push origin main
```

### Scenario 3: Pull v1 Updates into v2 (Keep v2 Current)

This is the key workflow - when you update v1, you want those changes in v2 too:

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Make sure you're on v2 branch
git checkout feature/v2-podcast-generation

# Fetch latest from v1
git fetch v1-upstream main

# Merge v1 changes into v2
git merge v1-upstream/main

# If there are conflicts, resolve them:
# 1. Open conflicting files
# 2. Look for <<<<<<< HEAD markers
# 3. Choose which version to keep
# 4. Remove conflict markers
# 5. Stage resolved files
git add <resolved-files>
git commit -m "Merge v1 updates into v2"

# Push updated v2
git push origin feature/v2-podcast-generation
```

### Scenario 4: Pull v2 Updates into v1 (Merge Back)

When v2 features are ready for production:

```bash
# First, make sure v2 is up to date with v1
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git fetch v1-upstream main
git merge v1-upstream/main

# Then merge v2 into v1
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git checkout main

# Merge v2 branch
git merge --no-ff /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2 feature/v2-podcast-generation

# Or use a different approach - cherry-pick specific commits
# git cherry-pick <commit-hash>
```

---

## Common Workflows Explained

### Morning Routine: Start v2 Development

```bash
# 1. Check if v1 has updates
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git pull origin main

# 2. Pull those updates into v2
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git checkout feature/v2-podcast-generation
git fetch v1-upstream main
git merge v1-upstream/main

# 3. Start working on v2
# ... develop features ...
```

### End of Day: Save v2 Progress

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Stage all changes
git add .

# Commit with descriptive message
git commit -m "WIP: Complete podcaster nodes implementation"

# Push to GitHub for backup
git push origin feature/v2-podcast-generation
```

### Weekly: Sync Everything

```bash
# 1. Update v1 from GitHub (if working across machines)
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git checkout main
git pull origin main

# 2. Update v2 from GitHub
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git checkout feature/v2-podcast-generation
git pull origin feature/v2-podcast-generation

# 3. Merge v1 updates into v2
git fetch v1-upstream main
git merge v1-upstream/main

# 4. Push merged v2
git push origin feature/v2-podcast-generation
```

---

## Git Branch Strategy

### Recommended Structure

```
hero_evidence_library/ (v1)
├── main                    # Production code
├── feature/bugfix-xyz      # Short-lived bug fixes
└── feature/enhancement-abc # Short-lived enhancements

evidence_library_v2/ (v2)
├── main                          # Mirrors v1 main
├── feature/v2-podcast-generation # Main v2 work
├── feature/v2-summary-generation # Future features
└── feature/v2-database-migration # Database work
```

### Creating New Feature Branches in v2

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2

# Create new branch from current v2 branch
git checkout feature/v2-podcast-generation
git checkout -b feature/v2-summary-generation

# Or create from v1 main
git checkout -b feature/v2-database-migration v1-upstream/main
```

---

## Conflict Resolution Guide

When merging v1 into v2, conflicts may occur:

```bash
# After running: git merge v1-upstream/main
# If you see conflicts:

Auto-merging backend/app/db.py
CONFLICT (content): Merge conflict in backend/app/db.py
Automatic merge failed; fix conflicts and then commit the result.

# Step 1: Check which files have conflicts
git status

# Step 2: Open conflicting file
# You'll see markers like:
<<<<<<< HEAD
# v2 code here
=======
# v1 code here
>>>>>>> v1-upstream/main

# Step 3: Resolve - choose one or combine:
# - Keep v2 changes: Delete <<<, ===, >>> and v1 section
# - Keep v1 changes: Delete <<<, ===, >>> and v2 section
# - Keep both: Delete markers, arrange code logically

# Step 4: Stage resolved file
git add backend/app/db.py

# Step 5: Complete merge
git commit -m "Merge v1 updates, resolved conflicts in db.py"
```

---

## Advanced: Selective Syncing

### Cherry-Pick Specific Commits from v1 to v2

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git checkout feature/v2-podcast-generation

# Find commit hash from v1
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git log --oneline -n 10
# Note the hash of the commit you want

# Cherry-pick into v2
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git cherry-pick <commit-hash>
```

### Ignore v2 Changes When Viewing v1 History

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library

# View v1 history without v2 noise
git log --oneline --first-parent main
```

---

## Safety Practices

### Before Major Operations: Create Backup

```bash
# Backup v1
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git tag backup-$(date +%Y%m%d) main
git push origin backup-$(date +%Y%m%d)

# Backup v2
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git tag backup-$(date +%Y%m%d) feature/v2-podcast-generation
git push origin backup-$(date +%Y%m%d)
```

### Undo Last Commit (If Needed)

```bash
# Undo last commit but keep changes
git reset --soft HEAD~1

# Undo last commit and discard changes (DANGEROUS)
git reset --hard HEAD~1

# Undo last pushed commit
git revert HEAD
git push origin <branch-name>
```

### Check What Changed

```bash
# See uncommitted changes
git diff

# See what's staged
git diff --staged

# See changes between branches
git diff main feature/v2-podcast-generation

# See file changes only
git diff --name-only main feature/v2-podcast-generation
```

---

## Quick Reference Commands

```bash
# Status check
git status                                    # See current changes
git branch                                    # See current branch
git remote -v                                 # See configured remotes

# Common operations
git add .                                     # Stage all changes
git commit -m "message"                       # Commit changes
git push origin <branch>                      # Push to GitHub

# Syncing
git fetch v1-upstream main                    # Get v1 updates
git merge v1-upstream/main                    # Merge v1 into v2
git pull origin <branch>                      # Pull from GitHub

# Branch management
git checkout <branch>                         # Switch branch
git checkout -b <new-branch>                  # Create and switch
git branch -d <branch>                        # Delete branch (safe)
git branch -D <branch>                        # Delete branch (force)

# Viewing history
git log --oneline -n 10                       # Recent commits
git log --graph --all --oneline               # Visual branch history
```

---

## Troubleshooting

### "Detached HEAD" State

```bash
# If you see: "You are in 'detached HEAD' state"
git checkout feature/v2-podcast-generation
```

### Accidentally Committed to Wrong Branch

```bash
# Save the commit
git log -1  # Note the commit hash

# Switch to correct branch
git checkout correct-branch

# Cherry-pick the commit
git cherry-pick <commit-hash>

# Go back and remove from wrong branch
git checkout wrong-branch
git reset --hard HEAD~1
```

### Merge Went Wrong, Start Over

```bash
# Abort merge in progress
git merge --abort

# Reset to before merge
git reset --hard HEAD~1
```

---

## Automated Sync Script (Optional)

Create a script to automate daily syncing:

```bash
#!/bin/bash
# File: ~/bin/sync-hero-repos.sh

echo "📦 Syncing HERO Evidence Library repositories..."

# Update v1
echo "\n✅ Updating v1..."
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
git checkout main
git pull origin main

# Update v2 and merge v1 changes
echo "\n✅ Updating v2 and merging v1 changes..."
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
git checkout feature/v2-podcast-generation
git pull origin feature/v2-podcast-generation
git fetch v1-upstream main
git merge v1-upstream/main

echo "\n✨ Sync complete!"
```

Make it executable:
```bash
chmod +x ~/bin/sync-hero-repos.sh
```

Run daily:
```bash
~/bin/sync-hero-repos.sh
```

---

## Summary

**Daily Workflow:**
1. Morning: `cd v2 && git fetch v1-upstream main && git merge v1-upstream/main`
2. Develop: `git add . && git commit -m "Feature work"`
3. Evening: `git push origin feature/v2-podcast-generation`

**When v1 Changes:**
```bash
cd v1 && git pull origin main
cd v2 && git fetch v1-upstream main && git merge v1-upstream/main
```

**When v2 Ready:**
```bash
# Merge v2 into v1 (requires testing)
cd v1 && git merge --no-ff ../evidence_library_v2 feature/v2-podcast-generation
```

---

**Created**: 2025-01-04  
**Status**: Ready to use  
**Owner**: Jamie Forrest
