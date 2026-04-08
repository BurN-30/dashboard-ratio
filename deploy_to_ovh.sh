#!/bin/bash
# TrackBoard - Deployment helper (rsync vers VPS)
#
# Pour la prod, prefere `git clone` directement sur le VPS et laisse Caddy
# gerer HTTPS automatiquement. Ce script est utile pour pousser des modifs
# locales rapidement sans passer par git.

set -e

OVH_HOST="${DEPLOY_HOST:-your-server-ip}"
OVH_USER="${DEPLOY_USER:-ubuntu}"
DOMAIN="${DOMAIN:-example.com}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/ubuntu/trackboard}"

echo "========================================"
echo "TrackBoard - Deploy to $OVH_USER@$OVH_HOST"
echo "Domain : $DOMAIN"
echo "========================================"
echo

# Step 1 - Docker
echo "[1/4] Checking Docker..."
ssh "$OVH_USER@$OVH_HOST" "docker --version" 2>/dev/null || {
    echo "Docker not found. Installing..."
    ssh "$OVH_USER@$OVH_HOST" "curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $OVH_USER"
    echo "Docker installed. Reconnect SSH and re-run this script."
    exit 1
}

# Step 2 - Deploy dir
echo "[2/4] Ensuring deploy dir..."
ssh "$OVH_USER@$OVH_HOST" "mkdir -p $DEPLOY_DIR"

# Step 3 - Sync files
echo "[3/4] Rsync files..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
rsync -avz \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.env' \
    --exclude 'cookies/' \
    "$SCRIPT_DIR/" "$OVH_USER@$OVH_HOST:$DEPLOY_DIR/"

# Step 4 - .env bootstrap
echo "[4/4] Bootstrap .env..."
ssh "$OVH_USER@$OVH_HOST" "cd $DEPLOY_DIR && [ -f .env ] || cp .env.example .env"

cat <<EOF

========================================
Files synced. Next steps on the VPS :

  ssh $OVH_USER@$OVH_HOST
  cd $DEPLOY_DIR
  nano .env       # remplir DOMAIN, ACME_EMAIL, JWT_SECRET, ADMIN_PASSWORD,
                  # POSTGRES_PASSWORD, HW_AGENT_TOKEN, credentials trackers
  docker compose up -d --build
  docker compose logs -f

  # Capture des cookies trackers (depuis l'IP du VPS, important !) :
  docker compose exec backend python capture_cookies.py "Sharewood" "https://sharewood.tv/login"

========================================
EOF

