#!/bin/bash
# Install uv on production server if not already installed
# uv is a fast Python package installer and resolver

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Installing uv Python package manager${NC}"
echo ""

# Check if uv is already installed
if command -v uv >/dev/null 2>&1; then
    UV_VERSION=$(uv --version)
    echo -e "${GREEN}✓ uv is already installed: $UV_VERSION${NC}"
    exit 0
fi

# Check if we're on macOS
if [[ "$(uname)" == "Darwin" ]]; then
    echo -e "${BLUE}Installing uv on macOS...${NC}"
    
    # Check if Homebrew is available
    if command -v brew >/dev/null 2>&1; then
        echo "Installing via Homebrew..."
        brew install uv
    else
        echo "Installing via curl script..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Add to PATH if installed to ~/.cargo/bin
        if [ -d "$HOME/.cargo/bin" ]; then
            export PATH="$HOME/.cargo/bin:$PATH"
            echo ""
            echo -e "${YELLOW}Note: Added ~/.cargo/bin to PATH for this session${NC}"
            echo "To make it permanent, add to your ~/.zshrc:"
            echo "  export PATH=\"\$HOME/.cargo/bin:\$PATH\""
        fi
    fi
else
    echo -e "${YELLOW}Installing via curl script (works on Linux too)...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH if installed to ~/.cargo/bin
    if [ -d "$HOME/.cargo/bin" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
        echo ""
        echo -e "${YELLOW}Note: Added ~/.cargo/bin to PATH for this session${NC}"
        echo "To make it permanent, add to your ~/.zshrc or ~/.bashrc:"
        echo "  export PATH=\"\$HOME/.cargo/bin:\$PATH\""
    fi
fi

# Verify installation
if command -v uv >/dev/null 2>&1; then
    UV_VERSION=$(uv --version)
    echo ""
    echo -e "${GREEN}✓ uv installed successfully: $UV_VERSION${NC}"
    echo ""
    echo "Usage:"
    echo "  uv pip install <package>    # Install package"
    echo "  uv pip install -r requirements.txt  # Install from requirements"
    echo "  uv pip list                 # List installed packages"
else
    echo -e "${YELLOW}Warning: uv installation may have completed but is not in PATH${NC}"
    echo "Try running: source ~/.zshrc (or ~/.bashrc) and then check with: uv --version"
fi

