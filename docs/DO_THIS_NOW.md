# Fix NumPy Issue - Do This Now

## Step 1: Fix NumPy (Run this on mac-mini RIGHT NOW)

SSH to mac-mini and run:

```bash
ssh mac-mini
cd ~/production/hero-evidence-library/backend
source venv/bin/activate
pip install "numpy<2.0" --upgrade
```

This will downgrade NumPy from 2.2.6 to a 1.x version that's compatible with PyTorch.

**Verify it worked:**
```bash
python3 -c "import numpy; import torch; print('Success! NumPy:', numpy.__version__)"
```

You should see: `Success! NumPy: 1.26.x` (or similar 1.x version)

## Step 2: Redeploy Updated Scripts

From your dev machine:

```bash
cd /Users/drjforrest/dev/projects/hero-counterforce/hero_evidence_library
./scripts/deploy_sync_scripts.sh
```

This deploys the updated sync script that will automatically check/fix NumPy in the future.

## Step 3: Run Sync Again

Back on mac-mini:

```bash
cd ~/production/hero-evidence-library
./scripts/sync_production_devonthink.sh
```

It should work now! The updated script will also verify NumPy compatibility before proceeding.

---

**Why this happened:** NumPy 2.x is incompatible with PyTorch (compiled with NumPy 1.x). We need NumPy <2.0 until dependencies are updated.

