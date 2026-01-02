# Quick Fix: NumPy Compatibility Issue

## The Problem

The sync script is failing because NumPy 2.2.6 is incompatible with PyTorch (which was compiled with NumPy 1.x).

## Immediate Fix

SSH to mac-mini and run this ONE command:

```bash
ssh mac-mini "cd ~/production/hero-evidence-library/backend && source venv/bin/activate && pip install 'numpy<2.0' --upgrade"
```

Or use the fix script (if deployed):

```bash
ssh mac-mini
cd ~/production/hero-evidence-library
./scripts/fix_production_numpy.sh
```

## Then Run Sync Again

After fixing NumPy:

```bash
cd ~/production/hero-evidence-library
./scripts/sync_production_devonthink.sh
```

## Verify It's Fixed

Test that imports work:

```bash
ssh mac-mini "cd ~/production/hero-evidence-library/backend && source venv/bin/activate && python3 -c 'import numpy; import torch; print(\"Success! NumPy:\", numpy.__version__)'"
```

You should see: `Success! NumPy: 1.26.x` (or similar 1.x version)

## Why This Happens

- NumPy 2.x introduced breaking changes
- PyTorch and rerankers were compiled with NumPy 1.x
- We need NumPy <2.0 until dependencies are updated

The updated sync script will automatically check and fix this in the future, but you need to fix it manually once first.

