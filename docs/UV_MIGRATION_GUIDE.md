# Migrating to `uv` for Dependency Management

## Why `uv`?

`uv` is a fast Python package manager written in Rust that:
- ✅ **10-100x faster** than pip
- ✅ **Better dependency resolution** - handles conflicts automatically
- ✅ **Drop-in replacement** for pip
- ✅ **Can resolve NumPy 2.0 conflicts** by finding compatible versions

## Installation

### On Your Mac (Development)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```

### On Server (mac-mini)
```bash
ssh mac-mini
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if not auto-added)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

### Basic Commands

```bash
# Install dependencies (replaces: pip install -r requirements.txt)
uv pip install -r requirements.txt

# Install with better conflict resolution
uv pip install -r requirements.txt --resolution=highest

# Sync dependencies (ensures exact versions match)
uv pip sync requirements.txt

# Install in existing venv
uv pip install -r requirements.txt --python .venv/bin/python
```

### Resolving NumPy Conflict

`uv` can automatically resolve the NumPy 2.0 conflict:

```bash
cd backend
source venv/bin/activate

# uv will find compatible versions automatically
uv pip install -r requirements.txt --resolution=highest
```

This will:
1. Find versions of `chonkie` and `opencv-python` compatible with NumPy 1.x
2. Or find versions of PyTorch compatible with NumPy 2.x
3. Resolve the conflict automatically

## Migration Steps

### Option 1: Use uv with existing venv (Recommended)

```bash
cd backend

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Use existing venv but install with uv
source venv/bin/activate
uv pip install -r requirements.txt --resolution=highest
```

### Option 2: Create new venv with uv

```bash
cd backend

# Remove old venv
rm -rf venv

# Create venv with uv (faster)
uv venv

# Activate and install
source venv/bin/activate
uv pip install -r requirements.txt
```

## Update deploy.sh

Update `deploy.sh` to use `uv`:

```bash
# Replace this section in deploy.sh:
pip install --upgrade pip
pip install -r requirements.txt

# With:
if command -v uv &> /dev/null; then
    echo "Using uv for faster dependency installation..."
    uv pip install -r requirements.txt --resolution=highest
else
    echo "uv not found, falling back to pip..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi
```

## Benefits

1. **Faster installs** - 10-100x faster than pip
2. **Better conflict resolution** - Handles NumPy 2.0 automatically
3. **Reproducible builds** - Better version locking
4. **Drop-in replacement** - Works with existing requirements.txt

## Troubleshooting

If `uv` can't resolve conflicts, you can still pin versions:

```bash
# In requirements.txt, add:
numpy<2.0.0  # Force NumPy 1.x
chonkie<1.5.0  # Use older chonkie that supports NumPy 1.x
```

Then:
```bash
uv pip install -r requirements.txt
```
