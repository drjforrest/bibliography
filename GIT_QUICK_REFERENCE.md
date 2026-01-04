# Git Quick Reference - HERO v1 + v2

## 🚀 Initial Setup (Run Once)

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
./scripts/setup_git.sh
```

This will:
- Create `feature/v2-podcast-generation` branch
- Add v1 as `v1-upstream` remote
- Fetch initial v1 state

---

## 📅 Daily Workflow

### Morning: Sync v1 → v2

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2
./scripts/sync_daily.sh
```

Or manually:
```bash
cd ~/dev/projects/hero-counterforce/evidence_library_v2
git fetch v1-upstream main
git merge v1-upstream/main
```

### During Day: Work on v2

```bash
cd ~/dev/projects/hero-counterforce/evidence_library_v2

# Edit files...

git add .
git commit -m "Add podcast generation feature"
git push origin feature/v2-podcast-generation
```

### Work on v1 (Bug Fixes)

```bash
cd ~/dev/projects/hero-counterforce/hero_evidence_library

# Edit files...

git add .
git commit -m "Fix: Resolve issue #123"
git push origin main

# Then sync to v2:
cd ~/dev/projects/hero-counterforce/evidence_library_v2
./scripts/sync_daily.sh
```

---

## 🔄 Common Operations

### Check Status
```bash
# v1 status
cd ~/dev/projects/hero-counterforce/hero_evidence_library && git status

# v2 status  
cd ~/dev/projects/hero-counterforce/evidence_library_v2 && git status
```

### See What Changed
```bash
# Uncommitted changes
git diff

# Changes between v1 and v2
git diff v1-upstream/main
```

### Commit Current Work
```bash
git add .
git commit -m "WIP: Podcast nodes implementation"
git push origin feature/v2-podcast-generation
```

### Undo Last Commit (Keep Changes)
```bash
git reset --soft HEAD~1
```

---

## ⚠️ Conflict Resolution

If you see conflicts during merge:

```bash
# 1. Check which files conflict
git status

# 2. Open conflicting files and look for:
<<<<<<< HEAD
# v2 code
=======
# v1 code  
>>>>>>> v1-upstream/main

# 3. Edit to resolve, remove markers

# 4. Stage resolved files
git add <file>

# 5. Complete merge
git commit
```

---

## 🎯 Branch Management

### Switch Between Branches
```bash
# Work on v2 features
git checkout feature/v2-podcast-generation

# Check v1 main
git checkout main
```

### Create New Feature Branch
```bash
git checkout feature/v2-podcast-generation
git checkout -b feature/v2-summaries
```

---

## 📊 Viewing History

```bash
# Recent commits
git log --oneline -n 10

# Visual branch history
git log --graph --all --oneline

# What's different from v1
git log v1-upstream/main..HEAD
```

---

## 🛟 Emergency Commands

### Abort Merge
```bash
git merge --abort
```

### Discard All Changes
```bash
git reset --hard HEAD
```

### Go Back to Clean State
```bash
git checkout feature/v2-podcast-generation
git reset --hard origin/feature/v2-podcast-generation
```

---

## 📍 File Locations

- **v1 Repo**: `/Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library/`
- **v2 Repo**: `/Users/drjforrest/dev/projects/hero-counterforce/evidence_library_v2/`
- **Setup Script**: `v2/scripts/setup_git.sh`
- **Sync Script**: `v2/scripts/sync_daily.sh`
- **Full Guide**: `v2/docs/GIT_WORKFLOW_GUIDE.md`

---

## ✅ Quick Checks

### Is v2 up to date with v1?
```bash
cd ~/dev/projects/hero-counterforce/evidence_library_v2
git fetch v1-upstream main
git log HEAD..v1-upstream/main
# If empty: up to date
# If shows commits: need to merge
```

### Where am I?
```bash
git branch --show-current
git status
```

### What remotes do I have?
```bash
git remote -v
```

---

**Created**: 2025-01-04  
**Owner**: Jamie Forrest
