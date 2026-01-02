#!/bin/bash
# Fix NumPy version incompatibility on production
# Downgrades NumPy to <2.0 for compatibility with torch and other modules

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$HOME/production/hero-evidence-library"
BACKEND_DIR="$PROJECT_DIR/backend"

echo -e "${BLUE}Fixing NumPy version incompatibility on production${NC}"
echo ""

if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}Error: Virtual environment not found${NC}"
    exit 1
fi

echo -e "${BLUE}Activating virtual environment...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate

# Check if uv is available
if command -v uv >/dev/null 2>&1; then
    PACKAGE_MANAGER="uv"
    echo -e "${BLUE}Using uv for package management${NC}"
else
    PACKAGE_MANAGER="pip"
    echo -e "${BLUE}Using pip for package management (uv not found)${NC}"
fi

echo -e "${BLUE}Checking current NumPy version...${NC}"
CURRENT_NUMPY=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "not installed")
echo "Current NumPy: $CURRENT_NUMPY"

if [[ "$CURRENT_NUMPY" == "not installed" ]] || [[ $(echo "$CURRENT_NUMPY" | cut -d. -f1) -ge 2 ]]; then
    echo -e "${BLUE}Downgrading NumPy to <2.0 for compatibility...${NC}"
    
    if [[ "$PACKAGE_MANAGER" == "uv" ]]; then
        uv pip install "numpy<2.0" --upgrade
    else
        pip install "numpy<2.0" --upgrade
    fi
    
    echo -e "${GREEN}✓ NumPy downgraded successfully${NC}"
    NEW_NUMPY=$(python3 -c "import numpy; print(numpy.__version__)")
    echo "New NumPy version: $NEW_NUMPY"
else
    echo -e "${GREEN}✓ NumPy version is already compatible (<2.0)${NC}"
fi

echo ""
echo -e "${BLUE}Testing import...${NC}"
if python3 -c "import numpy; import torch; print('✓ All imports successful')" 2>&1; then
    echo -e "${GREEN}✓ NumPy/Torch compatibility verified${NC}"
else
    echo -e "${YELLOW}Warning: Some issues may remain. Check the output above.${NC}"
fi

echo ""
echo -e "${GREEN}NumPy fix complete!${NC}"

