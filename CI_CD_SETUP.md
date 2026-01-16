# ContentEngine CI/CD Setup Guide

## Overview

Automated deployment with GitHub Actions that:
- ✅ Deploys on every push to main/master
- ✅ Handles secrets securely
- ✅ Manages database migrations automatically
- ✅ Restarts services
- ✅ Can be triggered manually
- ✅ No manual SSH or rsync needed

---

## Setup Steps

### Step 1: Generate SSH Key for GitHub Actions

```bash
# On your local machine, generate dedicated SSH key
ssh-keygen -t ed25519 -C "github-actions@contentengine" -f ~/.ssh/contentengine_deploy

# This creates:
# - ~/.ssh/contentengine_deploy (private key - for GitHub)
# - ~/.ssh/contentengine_deploy.pub (public key - for server)
```

### Step 2: Add Public Key to Server

```bash
# Copy public key to server
ssh-copy-id -i ~/.ssh/contentengine_deploy.pub ajohn@192.168.0.5

# OR manually:
cat ~/.ssh/contentengine_deploy.pub | ssh ajohn@192.168.0.5 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'

# Test it works
ssh -i ~/.ssh/contentengine_deploy ajohn@192.168.0.5 "echo 'SSH key works!'"
```

### Step 3: Add Secrets to GitHub Repository

Go to: `https://github.com/YOUR_USERNAME/ContentEngine/settings/secrets/actions`

Add these secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `SERVER_SSH_KEY` | Private key content | Copy from `~/.ssh/contentengine_deploy` |
| `SERVER_HOST` | Server IP/hostname | `192.168.0.5` |
| `SERVER_USER` | SSH username | `ajohn` |
| `SERVER_PATH` | Deploy directory | `/home/ajohn/ContentEngine` |

**How to copy private key:**
```bash
cat ~/.ssh/contentengine_deploy
# Copy entire output including:
# -----BEGIN OPENSSH PRIVATE KEY-----
# ...
# -----END OPENSSH PRIVATE KEY-----
```

---

## Handling .env and Secrets

### Option 1: Use GitHub Secrets (Recommended)

**Store each .env variable as a GitHub secret:**

```bash
# Add these to GitHub Secrets:
LINKEDIN_CLIENT_ID
LINKEDIN_CLIENT_SECRET
LINKEDIN_ACCESS_TOKEN
LINKEDIN_USER_SUB
ANTHROPIC_API_KEY
OPENAI_API_KEY
OLLAMA_HOST
```

**Then update workflow to create .env on server:**

Add this step to `.github/workflows/deploy.yml`:

```yaml
- name: Create .env file on server
  env:
    SERVER_USER: ${{ secrets.SERVER_USER }}
    SERVER_HOST: ${{ secrets.SERVER_HOST }}
    SERVER_PATH: ${{ secrets.SERVER_PATH }}
  run: |
    ssh $SERVER_USER@$SERVER_HOST "cat > $SERVER_PATH/.env << 'EOF'
    LINKEDIN_CLIENT_ID=${{ secrets.LINKEDIN_CLIENT_ID }}
    LINKEDIN_CLIENT_SECRET=${{ secrets.LINKEDIN_CLIENT_SECRET }}
    LINKEDIN_ACCESS_TOKEN=${{ secrets.LINKEDIN_ACCESS_TOKEN }}
    LINKEDIN_USER_SUB=${{ secrets.LINKEDIN_USER_SUB }}
    ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}
    OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
    OLLAMA_HOST=${{ secrets.OLLAMA_HOST }}
    HOST=0.0.0.0
    PORT=3000
    REDIRECT_URI=http://localhost:3000/callback
    EOF
    "
```

### Option 2: Pre-configure .env on Server (Simpler)

**Just set up .env once on the server manually:**

```bash
# SSH to server
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Create .env with your credentials
cp .env.example .env
nano .env
# Add all your tokens

# Make it persistent (won't be overwritten by CI/CD)
chmod 600 .env
```

**CI/CD will skip .env** (it's in rsync --exclude already)

---

## Database Handling

### Strategy 1: Persistent Database (Recommended)

**Keep database on server, CI/CD never touches it:**

- Database lives at `/home/ajohn/ContentEngine/content.db`
- CI/CD excludes it from sync (already done in workflow)
- Migrations run automatically on deploy
- Data persists across deployments

**One-time setup:**
```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Initialize database
uv run content-engine list  # Creates database if missing

# Migrate OAuth tokens
uv run python scripts/migrate_oauth.py
```

### Strategy 2: Database Backup/Restore

**Add database backup step to workflow:**

```yaml
- name: Backup database before deploy
  env:
    SERVER_USER: ${{ secrets.SERVER_USER }}
    SERVER_HOST: ${{ secrets.SERVER_HOST }}
    SERVER_PATH: ${{ secrets.SERVER_PATH }}
  run: |
    ssh $SERVER_USER@$SERVER_HOST "cd $SERVER_PATH && cp content.db content.db.backup.\$(date +%Y%m%d-%H%M%S) || true"
```

---

## Ollama Setup (One-Time)

Ollama needs to be installed and configured on the server once:

```bash
ssh ajohn@192.168.0.5

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3:8b

# Enable as systemd service
sudo systemctl enable ollama
sudo systemctl start ollama

# Verify
curl http://localhost:11434/api/tags
```

**CI/CD assumes Ollama is already running** - it won't install it.

---

## Systemd Service for Auto-Restart

Create a systemd service so CI/CD can restart the app automatically.

### Create Service File

```bash
ssh ajohn@192.168.0.5

# Create user service directory
mkdir -p ~/.config/systemd/user

# Create service file
nano ~/.config/systemd/user/content-engine-worker.service
```

**Service file content:**

```ini
[Unit]
Description=Content Engine Background Worker
After=network.target ollama.service

[Service]
Type=simple
WorkingDirectory=/home/ajohn/ContentEngine
Environment="PATH=/home/ajohn/.cargo/bin:/usr/bin:/bin"
ExecStart=/home/ajohn/.cargo/bin/uv run content-worker
Restart=always
RestartSec=60

# Logging
StandardOutput=append:/home/ajohn/ContentEngine/worker.log
StandardError=append:/home/ajohn/ContentEngine/worker-error.log

[Install]
WantedBy=default.target
```

### Enable and Start Service

```bash
# Reload systemd
systemctl --user daemon-reload

# Enable service (start on boot)
systemctl --user enable content-engine-worker.service

# Start service
systemctl --user start content-engine-worker.service

# Check status
systemctl --user status content-engine-worker.service

# View logs
journalctl --user -u content-engine-worker.service -f
```

### Update CI/CD to Restart Service

The workflow already includes this step:

```yaml
- name: Restart services (if using systemd)
  run: |
    ssh $SERVER_USER@$SERVER_HOST "systemctl --user restart content-engine-worker.service 2>/dev/null || true"
```

---

## Complete Workflow

Here's what happens when you push to main:

```
1. Push to GitHub main branch
   ↓
2. GitHub Actions triggers
   ↓
3. Actions checkout code
   ↓
4. Set up SSH with server
   ↓
5. Rsync code to server (excludes .env, db, venv)
   ↓
6. Install dependencies (uv sync)
   ↓
7. Run database migrations
   ↓
8. Verify deployment (import test)
   ↓
9. Restart systemd service
   ↓
10. Deployment complete! ✅
```

**No manual steps needed!**

---

## Testing CI/CD

### Test 1: Manual Trigger

```bash
# Go to GitHub Actions tab
# Click "Deploy ContentEngine" workflow
# Click "Run workflow" button
# Select "main" branch
# Click "Run workflow"

# Watch it deploy!
```

### Test 2: Push to Main

```bash
cd ~/Work/ContentEngine

# Make a small change
echo "# Test deployment" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD deployment"
git push origin main

# Check GitHub Actions tab to see deployment
```

### Test 3: Verify on Server

```bash
# SSH to server
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Check git log (should show latest commit)
git log -1

# Test the app
uv run content-engine list

# Check service status
systemctl --user status content-engine-worker.service
```

---

## Advanced: Multi-Environment Setup

### Add Staging Environment

Create separate workflow for staging:

**.github/workflows/deploy-staging.yml:**

```yaml
name: Deploy to Staging

on:
  push:
    branches:
      - develop

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      # Same as production but uses:
      # - secrets.STAGING_SERVER_HOST
      # - secrets.STAGING_SERVER_USER
      # - secrets.STAGING_SERVER_PATH
```

### Environment-Specific Secrets

In GitHub:
- `PROD_SERVER_HOST` = 192.168.0.5
- `STAGING_SERVER_HOST` = 192.168.0.6
- Etc.

---

## Rollback Strategy

### Option 1: Revert Git Commit

```bash
# On local machine
cd ~/Work/ContentEngine

# Revert to previous commit
git revert HEAD

# Push (triggers deployment of reverted code)
git push origin main
```

### Option 2: Manual Rollback on Server

```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Reset to specific commit
git reset --hard <commit-hash>

# Reinstall dependencies
uv sync

# Restart service
systemctl --user restart content-engine-worker.service
```

---

## Monitoring Deployments

### Add Slack/Discord Notifications

Add to workflow (at the end):

```yaml
- name: Notify on deployment
  if: always()
  env:
    DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
  run: |
    curl -X POST $DISCORD_WEBHOOK \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"🚀 ContentEngine deployed with status: ${{ job.status }}\"}"
```

### View Deployment History

Go to: `https://github.com/YOUR_USERNAME/ContentEngine/actions`

See:
- All deployments
- Success/failure status
- Logs for each step
- Deployment time

---

## Troubleshooting

### Issue: "Permission denied (publickey)"

**Cause:** SSH key not set up correctly

**Fix:**
```bash
# Verify key is in GitHub secrets
# Verify public key is on server
ssh ajohn@192.168.0.5 "cat ~/.ssh/authorized_keys | grep github-actions"

# Test SSH manually with same key
ssh -i ~/.ssh/contentengine_deploy ajohn@192.168.0.5
```

### Issue: "uv: command not found"

**Cause:** uv not in PATH for SSH sessions

**Fix:**
```yaml
# Update workflow to use full path
ssh $SERVER_USER@$SERVER_HOST "cd $SERVER_PATH && /home/ajohn/.cargo/bin/uv sync"
```

### Issue: Database locked

**Cause:** Service running while migration tries to run

**Fix:** Stop service before migrations:

```yaml
- name: Stop service before deployment
  run: |
    ssh $SERVER_USER@$SERVER_HOST "systemctl --user stop content-engine-worker.service || true"

# ... deploy steps ...

- name: Start service after deployment
  run: |
    ssh $SERVER_USER@$SERVER_HOST "systemctl --user start content-engine-worker.service"
```

---

## Security Checklist

- [ ] SSH key is dedicated to GitHub Actions (not your personal key)
- [ ] Private key is stored in GitHub Secrets (not in code)
- [ ] Server allows key-based SSH only (no password auth)
- [ ] .env file is excluded from git and rsync
- [ ] Secrets are in GitHub Secrets (not in workflow file)
- [ ] Database is excluded from sync (data safety)
- [ ] Server user has minimal permissions (not root)

---

## Cost & Performance

**GitHub Actions free tier:**
- 2,000 minutes/month for private repos
- Unlimited for public repos

**Typical deployment:**
- Takes 2-5 minutes
- Uses ~5 minutes of Actions time
- Can deploy 400+ times/month on free tier

**Server requirements:**
- No changes - same as before
- No additional services needed
- Just needs SSH access

---

## Next Steps

1. **Generate SSH key:**
   ```bash
   ssh-keygen -t ed25519 -C "github-actions@contentengine" -f ~/.ssh/contentengine_deploy
   ```

2. **Add to server:**
   ```bash
   ssh-copy-id -i ~/.ssh/contentengine_deploy.pub ajohn@192.168.0.5
   ```

3. **Add GitHub secrets:**
   - Go to repo settings → Secrets
   - Add: SERVER_SSH_KEY, SERVER_HOST, SERVER_USER, SERVER_PATH

4. **Set up .env on server once:**
   ```bash
   ssh ajohn@192.168.0.5
   cd ~/ContentEngine
   cp .env.example .env
   nano .env  # Add credentials
   ```

5. **Test deployment:**
   ```bash
   # Make a change
   git commit -am "Test CI/CD"
   git push origin main

   # Watch GitHub Actions tab
   ```

6. **(Optional) Set up systemd service:**
   ```bash
   # Follow "Systemd Service" section above
   ```

---

**Last Updated:** 2026-01-14

**Status:** Ready to implement

**Time to set up:** 15-30 minutes

**Benefit:** Never SSH manually again! Just `git push` and it deploys.
