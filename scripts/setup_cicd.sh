#!/bin/bash
# Quick setup script for CI/CD

set -e

echo "🚀 ContentEngine CI/CD Setup"
echo "============================"
echo ""

# Step 1: Generate SSH key
echo "📝 Step 1: Generate SSH Key for GitHub Actions"
echo ""

if [ -f ~/.ssh/contentengine_deploy ]; then
    echo "⚠️  SSH key already exists at ~/.ssh/contentengine_deploy"
    read -p "Regenerate? (y/N): " regenerate
    if [[ $regenerate != "y" && $regenerate != "Y" ]]; then
        echo "Using existing key..."
    else
        rm ~/.ssh/contentengine_deploy ~/.ssh/contentengine_deploy.pub
        ssh-keygen -t ed25519 -C "github-actions@contentengine" -f ~/.ssh/contentengine_deploy -N ""
    fi
else
    ssh-keygen -t ed25519 -C "github-actions@contentengine" -f ~/.ssh/contentengine_deploy -N ""
fi

echo "✅ SSH key generated"
echo ""

# Step 2: Add public key to server
echo "📤 Step 2: Add Public Key to Server"
echo ""

read -p "Server hostname/IP (default: 192.168.0.5): " server_host
server_host=${server_host:-192.168.0.5}

read -p "Server username (default: ajohn): " server_user
server_user=${server_user:-ajohn}

read -p "Deploy path (default: /home/ajohn/ContentEngine): " deploy_path
deploy_path=${deploy_path:-/home/ajohn/ContentEngine}

echo "Copying public key to $server_user@$server_host..."
ssh-copy-id -i ~/.ssh/contentengine_deploy.pub $server_user@$server_host

echo "✅ Public key added to server"
echo ""

# Step 3: Test SSH connection
echo "🧪 Step 3: Test SSH Connection"
echo ""

if ssh -i ~/.ssh/contentengine_deploy -o BatchMode=yes $server_user@$server_host "echo 'Connection successful!'" 2>/dev/null; then
    echo "✅ SSH connection works!"
else
    echo "❌ SSH connection failed. Please check your server access."
    exit 1
fi
echo ""

# Step 4: Display GitHub Secrets to add
echo "🔑 Step 4: Add These Secrets to GitHub"
echo ""
echo "Go to: https://github.com/YOUR_USERNAME/ContentEngine/settings/secrets/actions"
echo ""
echo "Add the following secrets:"
echo ""
echo "SECRET NAME         | VALUE"
echo "------------------- | -----"
echo "SERVER_SSH_KEY      | (See below - copy entire private key)"
echo "SERVER_HOST         | $server_host"
echo "SERVER_USER         | $server_user"
echo "SERVER_PATH         | $deploy_path"
echo ""

echo "📋 Copy this private key for SERVER_SSH_KEY:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat ~/.ssh/contentengine_deploy
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 5: Set up .env on server
echo "⚙️  Step 5: Set Up .env on Server (One-Time)"
echo ""

read -p "Set up .env on server now? (Y/n): " setup_env
if [[ $setup_env != "n" && $setup_env != "N" ]]; then
    echo "Checking if .env exists on server..."

    if ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "test -f $deploy_path/.env"; then
        echo "✅ .env already exists on server"
    else
        echo "Creating .env from template..."
        ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "cd $deploy_path && cp .env.example .env"
        echo "⚠️  Please SSH to server and edit .env with your credentials:"
        echo "   ssh $server_user@$server_host"
        echo "   cd $deploy_path"
        echo "   nano .env"
    fi
fi
echo ""

# Step 6: Set up systemd service (optional)
echo "🔧 Step 6: Set Up Systemd Service (Optional)"
echo ""

read -p "Set up systemd service for auto-restart? (Y/n): " setup_systemd
if [[ $setup_systemd != "n" && $setup_systemd != "N" ]]; then
    echo "Creating systemd service on server..."

    # Copy service file to server
    ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "mkdir -p ~/.config/systemd/user"
    scp -i ~/.ssh/contentengine_deploy systemd/content-engine-worker.service $server_user@$server_host:~/.config/systemd/user/

    # Update paths in service file
    ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "sed -i 's|/home/ajohn/ContentEngine|$deploy_path|g' ~/.config/systemd/user/content-engine-worker.service"
    ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "sed -i 's|/home/ajohn/.cargo/bin|~/.cargo/bin|g' ~/.config/systemd/user/content-engine-worker.service"

    # Enable and start service
    ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "systemctl --user daemon-reload"
    ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "systemctl --user enable content-engine-worker.service"
    ssh -i ~/.ssh/contentengine_deploy $server_user@$server_host "systemctl --user start content-engine-worker.service"

    echo "✅ Systemd service set up and running"
    echo ""
    echo "Check status with: ssh $server_user@$server_host 'systemctl --user status content-engine-worker.service'"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CI/CD Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "1. Add secrets to GitHub (see above)"
echo "2. Make sure .env is configured on server"
echo "3. Test deployment:"
echo "   git commit -am 'Test CI/CD'"
echo "   git push origin main"
echo "4. Watch GitHub Actions tab for deployment"
echo ""
echo "That's it! Future deployments happen automatically on push."
echo ""
