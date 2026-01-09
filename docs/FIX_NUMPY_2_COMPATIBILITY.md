# Fix NumPy 2.0 Compatibility Issue

## Problem

NumPy 2.0 was released, but PyTorch (used by `rerankers`) hasn't been updated to support it yet. This causes import errors:

```
UserWarning: Failed to initialize NumPy: _ARRAY_API not found
```

## Solution

Pin NumPy to version <2.0.0 in both `requirements.txt` and `pyproject.toml`.

## Fix Applied

Added to `backend/requirements.txt`:
```
numpy<2.0.0  # Pinned: PyTorch/rerankers not compatible with NumPy 2.0 yet
```

Added to `backend/pyproject.toml`:
```
"numpy<2.0.0",  # PyTorch/rerankers not compatible with NumPy 2.0 yet
```

## On Server: Reinstall Dependencies

### Option 1: Use `uv` (Recommended - Better Conflict Resolution)

```bash
cd ~/production/hero-evidence-library/backend

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Use uv to resolve conflicts automatically
source venv/bin/activate
uv pip install -r requirements.txt --resolution=highest
```

`uv` will automatically find compatible versions of all packages.

### Option 2: Use pip (Manual Fix)

```bash
cd ~/production/hero-evidence-library/backend
source venv/bin/activate
pip install "numpy<2.0.0" --force-reinstall
pip install -r requirements.txt --force-reinstall
```

**Note**: You may still see dependency conflicts with pip. `uv` handles this better.

## Verification

After reinstalling, verify NumPy version:
```bash
python -c "import numpy; print(numpy.__version__)"
```

Should show version like `1.26.x` (not `2.x.x`).
