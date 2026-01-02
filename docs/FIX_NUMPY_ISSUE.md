# Fix NumPy Compatibility Issue

## Problem

Production environment has NumPy 2.2.6, but PyTorch and other modules were compiled with NumPy 1.x and cannot run with NumPy 2.x.

Error message:

```
A module that was compiled using NumPy 1.x cannot be run in
NumPy 2.2.6 as it may crash. To support both 1.x and 2.x
versions of NumPy, modules must be compiled with NumPy 2.0.
```

## Quick Fix

SSH to mac-mini and run:

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
./scripts/fix_production_numpy.sh
```

Or manually:

```bash
ssh mac-mini
cd ~/production/hero-evidence-library/backend
source venv/bin/activate
pip install "numpy<2.0" --upgrade
```

## Verify Fix

Test that imports work:

```bash
python3 -c "import numpy; import torch; print('Success!')"
```

## After Fixing

Once NumPy is downgraded, you can run the sync script again:

```bash
cd ~/production/hero-evidence-library
./scripts/sync_production_devonthink.sh
```

## Prevention

The sync script now automatically checks and fixes NumPy compatibility before running. However, if you manually install packages, be aware that:

- NumPy 2.x breaks compatibility with older PyTorch versions
- Use `pip install "numpy<2.0"` when installing NumPy explicitly
- The sync script will automatically downgrade NumPy if needed

## Long-term Solution

When PyTorch and other dependencies fully support NumPy 2.x, you can upgrade:

1. Upgrade PyTorch to a version that supports NumPy 2.x
2. Upgrade rerankers to a version that supports NumPy 2.x
3. Then upgrade NumPy to 2.x

For now, staying on NumPy <2.0 is the safest approach.
