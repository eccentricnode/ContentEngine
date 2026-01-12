#!/bin/bash
set -e

SERVER="ajohn@192.168.0.5"
PASSWORD="Godisgreat14"

echo "🚀 Content Engine Server Setup"
echo "================================"

# Install sshpass if not present
if ! command -v sshpass &> /dev/null; then
    echo "📦 Installing sshpass..."
    sudo pacman -S --noconfirm sshpass || {
        echo "⚠️  Could not install sshpass. Please run: sudo pacman -S sshpass"
        exit 1
    }
fi

# Copy SSH key to server
echo "🔑 Setting up SSH key authentication..."
sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no $SERVER 2>/dev/null || echo "SSH key may already be installed"

# Test SSH connection
echo "✅ Testing SSH connection..."
ssh $SERVER "echo 'Connected successfully!'" || {
    echo "❌ SSH connection failed"
    exit 1
}

# Check if ContentEngine exists
echo "📁 Checking for ContentEngine on server..."
if ssh $SERVER "test -d ~/ContentEngine"; then
    echo "✅ ContentEngine directory exists"
    echo "🔄 Pulling latest changes..."
    ssh $SERVER "cd ~/ContentEngine && git pull origin master"
else
    echo "📥 Cloning ContentEngine..."
    ssh $SERVER "git clone git@github.com:eccentricnode/ContentEngine.git ~/ContentEngine"
fi

# Configure git on server
echo "⚙️  Configuring git..."
ssh $SERVER "cd ~/ContentEngine && git config user.name 'Austin Johnson' && git config user.email 'austin@example.com'"

# Check for uv
echo "🔍 Checking for uv package manager..."
if ssh $SERVER "command -v uv &> /dev/null"; then
    echo "✅ uv is installed"
else
    echo "📦 Installing uv..."
    ssh $SERVER "curl -LsSf https://astral.sh/uv/install.sh | sh"
    ssh $SERVER "source ~/.cargo/env"
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
ssh $SERVER "cd ~/ContentEngine && ~/.cargo/bin/uv sync"

# Check for Ollama
echo "🤖 Checking for Ollama..."
if ssh $SERVER "command -v ollama &> /dev/null"; then
    echo "✅ Ollama is installed"

    # Check if llama3:8b is pulled
    if ssh $SERVER "ollama list | grep -q llama3:8b"; then
        echo "✅ llama3:8b model is pulled"
    else
        echo "📥 Pulling llama3:8b model..."
        ssh $SERVER "ollama pull llama3:8b"
    fi
else
    echo "⚠️  Ollama not found. Install with: curl -fsSL https://ollama.com/install.sh | sh"
fi

# Create context directory
echo "📁 Creating context directory..."
ssh $SERVER "mkdir -p ~/ContentEngine/context"

# Set up environment file
echo "📝 Setting up .env file..."
ssh $SERVER "test -f ~/ContentEngine/.env || echo 'Setting up .env file - you may need to add tokens manually'"

# Test the setup
echo "🧪 Testing Content Engine..."
ssh $SERVER "cd ~/ContentEngine && ~/.cargo/bin/uv run python -c 'from lib import context_capture; print(\"✅ Import successful\")'"

echo ""
echo "✅ Server setup complete!"
echo ""
echo "Next steps:"
echo "1. SSH to server: ssh $SERVER"
echo "2. Add LinkedIn tokens to ~/ContentEngine/.env"
echo "3. Test context capture: cd ~/ContentEngine && uv run content-engine capture-context"
echo "4. Run Ralph: cd ~/ContentEngine && ./scripts/ralph/ralph.sh 20"
