#!/bin/bash

# Setup script for dedicated API domain via Cloudflare Tunnel
# This configures api.counterforce-hero.tech to route to backend port 8400

set -e

echo "🔧 Setting up API domain for hero-evidence-library"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if cloudflared config exists (better check than hostname)
CLOUDFLARED_CONFIG="$HOME/.cloudflared/config.yml"
if [ ! -f "$CLOUDFLARED_CONFIG" ]; then
    print_warning "Cloudflare tunnel config not found - this script should be run on the production server"
    print_warning "Run: ssh mac-mini 'cd ~/production/hero-evidence-library && ./scripts/setup-api-domain.sh'"
    exit 1
fi

# CLOUDFLARED_CONFIG already checked above

print_status "Backing up existing config..."
cp "$CLOUDFLARED_CONFIG" "${CLOUDFLARED_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Extract tunnel ID from existing config
TUNNEL_ID=$(grep -E '^tunnel:' "$CLOUDFLARED_CONFIG" | head -1 | awk '{print $2}' | tr -d '<>')
CREDENTIALS_FILE=$(grep -E '^credentials-file:' "$CLOUDFLARED_CONFIG" | head -1 | awk '{print $2}')

if [ -z "$TUNNEL_ID" ]; then
    print_error "Could not extract tunnel ID from config"
    exit 1
fi

print_status "Found tunnel ID: $TUNNEL_ID"

# Create new config with API domain
print_status "Creating new tunnel configuration..."
cat > "$CLOUDFLARED_CONFIG" << EOF
tunnel: $TUNNEL_ID
credentials-file: $CREDENTIALS_FILE

ingress:
  # Frontend (Next.js)
  - hostname: library.counterforce-hero.tech
    service: http://localhost:3400
  
  # Backend API (FastAPI)
  - hostname: api.counterforce-hero.tech
    service: http://localhost:8400
  
  # Catch-all (must be last)
  - service: http_status:404
EOF

print_status "✅ Tunnel configuration updated"

# Update frontend environment
print_status "Updating frontend environment..."
FRONTEND_ENV="$HOME/production/hero-evidence-library/frontend/nextjs-app/.env.local"
if [ -f "$FRONTEND_ENV" ]; then
    # Backup existing
    cp "$FRONTEND_ENV" "${FRONTEND_ENV}.backup.$(date +%Y%m%d_%H%M%S)"
fi

cat > "$FRONTEND_ENV" << 'EOF'
# Use dedicated API domain in production
NEXT_PUBLIC_API_URL=https://api.counterforce-hero.tech
BACKEND_URL=http://localhost:8400
EOF

print_status "✅ Frontend environment updated"

# Restart tunnel
print_status "Restarting Cloudflare tunnel..."
launchctl unload ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist 2>/dev/null || true
sleep 2
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.hero-evidence-library.plist

print_status "✅ Tunnel restarted"

echo ""
print_status "Next steps:"
echo "  1. Add DNS CNAME record in Cloudflare Dashboard:"
echo "     - Type: CNAME"
echo "     - Name: api"
echo "     - Target: ${TUNNEL_ID}.cfargotunnel.com"
echo "     - Proxy: Proxied (orange cloud) ✅"
echo ""
echo "  2. Wait 1-2 minutes for DNS propagation"
echo ""
echo "  3. Test API domain:"
echo "     curl https://api.counterforce-hero.tech/docs"
echo ""
echo "  4. Rebuild frontend to pick up new API URL:"
echo "     cd ~/production/hero-evidence-library/frontend/nextjs-app"
echo "     npm run build"
echo "     # Restart frontend service"
echo ""
print_status "🎉 API domain setup complete!"
print_warning "⚠️  Don't forget to add the DNS record in Cloudflare!"

