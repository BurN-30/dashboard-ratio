#!/bin/bash
# Dashboard V2 - OVH Deployment Script
# Run this locally to deploy to your OVH server

set -e

# Configuration - Edit these values for your setup
OVH_HOST="${DEPLOY_HOST:-your-server-ip}"
OVH_USER="${DEPLOY_USER:-ubuntu}"
DOMAIN="${DOMAIN:-example.com}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/ubuntu/dashboard-v2}"

echo "========================================"
echo "Dashboard V2 - OVH Deployment"
echo "========================================"
echo ""
echo "This script will:"
echo "1. Check if Docker is installed on OVH"
echo "2. Copy dashboard-v2 files to OVH"
echo "3. Configure and start the services"
echo ""
echo "Target: $OVH_USER@$OVH_HOST"
echo "Domain: $DOMAIN"
echo ""

# Step 1: Check Docker on remote
echo "[Step 1/5] Checking Docker installation..."
ssh $OVH_USER@$OVH_HOST "docker --version" 2>/dev/null || {
    echo "Docker not found. Installing Docker..."
    ssh $OVH_USER@$OVH_HOST "curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker ubuntu"
    echo "Docker installed. Please reconnect SSH and run this script again."
    exit 1
}

echo "[Step 2/5] Creating deployment directory..."
ssh $OVH_USER@$OVH_HOST "mkdir -p $DEPLOY_DIR"

echo "[Step 3/5] Copying files to OVH..."
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
rsync -avz --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
    "$SCRIPT_DIR/" "$OVH_USER@$OVH_HOST:$DEPLOY_DIR/"

echo "[Step 4/5] Setting up environment..."
ssh $OVH_USER@$OVH_HOST "cd $DEPLOY_DIR && if [ ! -f .env ]; then cp .env.example .env; fi"

echo ""
echo "========================================"
echo "Files copied! Next steps:"
echo "========================================"
echo ""
echo "1. SSH into OVH:"
echo "   ssh $OVH_USER@$OVH_HOST"
echo ""
echo "2. Edit the .env file:"
echo "   cd $DEPLOY_DIR && nano .env"
echo ""
echo "3. Configure these critical values:"
echo "   - DOMAIN=your-domain.com"
echo "   - JWT_SECRET=(generate with: openssl rand -hex 32)"
echo "   - ADMIN_PASSWORD=your-secure-password"
echo "   - POSTGRES_PASSWORD=(generate with: openssl rand -hex 16)"
echo "   - HW_AGENT_TOKEN=(generate with: openssl rand -hex 16)"
echo "   - Tracker credentials (SW_*, GF_*, TOS_*, etc.)"
echo ""
echo "4. Build and start:"
echo "   docker compose build"
echo "   docker compose up -d"
echo ""
echo "5. Check logs:"
echo "   docker compose logs -f"
echo ""
