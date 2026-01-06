#!/bin/bash

# Deployment script for Content Engine to server at 192.168.0.5

set -e  # Exit on error

SERVER_HOST="192.168.0.5"
SERVER_USER="ajohn"
DEPLOY_PATH="/home/ajohn/ContentEngine"

echo "=========================================="
echo "Content Engine Deployment"
echo "=========================================="
echo ""

# Check if server is reachable
echo "🔍 Checking server connectivity..."
if ! ping -c 1 "$SERVER_HOST" &> /dev/null; then
    echo "❌ Error: Cannot reach server at $SERVER_HOST"
    exit 1
fi
echo "✅ Server is reachable"
echo ""

# Create deployment directory on server if it doesn't exist
echo "📁 Creating deployment directory on server..."
ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $DEPLOY_PATH"
echo ""

# Sync code to server (excluding .git, __pycache__, etc.)
echo "📤 Syncing code to server..."
rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='*.log' \
    ./ "$SERVER_USER@$SERVER_HOST:$DEPLOY_PATH/"

echo ""
echo "📦 Installing dependencies on server..."
ssh "$SERVER_USER@$SERVER_HOST" "cd $DEPLOY_PATH && uv sync"

echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. SSH into server: ssh $SERVER_USER@$SERVER_HOST"
echo "2. Navigate to project: cd $DEPLOY_PATH"
echo "3. Set up .env file with credentials"
echo "4. Test connection: uv run python -m agents.linkedin.test_connection"
echo "5. Post test: uv run python -m agents.linkedin.post 'Test post' --dry-run"
echo ""
