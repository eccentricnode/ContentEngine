# ContentEngine Deployment Checklist

## Pre-Deployment Verification

### Server Requirements Check

**Before running deploy.sh, verify these on the target server (192.168.0.5):**

- [ ] **SSH Access Working**
  ```bash
  ssh ajohn@192.168.0.5
  ```

- [ ] **Python 3.11+ Installed**
  ```bash
  ssh ajohn@192.168.0.5 "python3 --version"
  # Should show 3.11 or higher
  ```

- [ ] **uv Package Manager Installed**
  ```bash
  ssh ajohn@192.168.0.5 "command -v uv"
  # If not installed, run: scripts/setup_server.sh
  ```

- [ ] **Ollama Installed & Running** (Required for context-capture)
  ```bash
  ssh ajohn@192.168.0.5 "systemctl status ollama"
  # If not running: systemctl start ollama
  ```

- [ ] **llama3:8b Model Pulled**
  ```bash
  ssh ajohn@192.168.0.5 "ollama list | grep llama3:8b"
  # If not present: ollama pull llama3:8b
  ```

- [ ] **Sufficient Disk Space** (at least 10GB for Ollama models + data)
  ```bash
  ssh ajohn@192.168.0.5 "df -h /home"
  ```

---

## Deployment Issues & Fixes

### Issue 1: .env File Not Synced

**Problem:** The deploy.sh script excludes `.env` from sync (line 36)

**Solution:**
```bash
# After deployment, manually copy .env
scp .env ajohn@192.168.0.5:~/ContentEngine/.env

# OR create it manually on server
ssh ajohn@192.168.0.5
cd ~/ContentEngine
cp .env.example .env
nano .env  # Add your credentials
```

**Required .env variables:**
- `LINKEDIN_CLIENT_ID` - From LinkedIn Developer app
- `LINKEDIN_CLIENT_SECRET` - From LinkedIn Developer app
- `LINKEDIN_ACCESS_TOKEN` - From OAuth flow (see below)
- `LINKEDIN_USER_SUB` - From OAuth flow
- `OLLAMA_HOST` - Should be `http://192.168.0.5:11434` or `http://localhost:11434`

---

### Issue 2: OAuth Tokens Need Server Setup

**Problem:** OAuth tokens stored in local database won't transfer

**Solutions:**

**Option A: Migrate Database**
```bash
# Copy database from local to server
scp content.db ajohn@192.168.0.5:~/ContentEngine/content.db
```

**Option B: Re-run OAuth Flow on Server**
```bash
# SSH to server
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Start OAuth server (requires GUI/browser access)
uv run python -m agents.linkedin.oauth_server

# Then migrate tokens to database
uv run python scripts/migrate_oauth.py
```

**Option C: Manual Token Entry**
```bash
# If you have tokens already, just add to .env
# Then migrate to database:
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run python scripts/migrate_oauth.py"
```

---

### Issue 3: Database Migrations

**Problem:** Database schema might be different between local and server

**Solution:**
```bash
# On server, run migrations
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run python scripts/migrate_database_schema.py"

# OR start fresh (if no important data)
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && rm -f content.db && uv run content-engine list"
# This will auto-create new database
```

---

### Issue 4: Ollama Not Running

**Problem:** Context capture fails with "Connection refused to Ollama"

**Solution:**
```bash
# Check if Ollama is running
ssh ajohn@192.168.0.5 "systemctl status ollama"

# If not running, start it
ssh ajohn@192.168.0.5 "systemctl start ollama"

# Enable on boot
ssh ajohn@192.168.0.5 "systemctl enable ollama"

# Verify it's accessible
ssh ajohn@192.168.0.5 "curl http://localhost:11434/api/tags"
```

---

### Issue 5: Background Worker Not Set Up

**Problem:** Scheduled posts won't publish automatically

**Solution:**
```bash
# Set up cron job on server
ssh ajohn@192.168.0.5

# Edit crontab
crontab -e

# Add this line (runs every 15 minutes)
*/15 * * * * cd /home/ajohn/ContentEngine && /home/ajohn/.cargo/bin/uv run content-worker >> /tmp/content-worker.log 2>&1
```

---

### Issue 6: File Permissions

**Problem:** Scripts might not be executable

**Solution:**
```bash
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && chmod +x scripts/*.sh scripts/*.py"
```

---

### Issue 7: Port Conflicts

**Problem:** OAuth server needs port 3000 but it's already in use

**Check:**
```bash
ssh ajohn@192.168.0.5 "netstat -tuln | grep 3000"
```

**Solution:**
Update `.env` to use different port:
```
PORT=3001
REDIRECT_URI=http://localhost:3001/callback
```

---

## Deployment Process (Step-by-Step)

### Step 1: Initial Server Setup (First Time Only)

```bash
# Run from your local machine
cd ~/Work/ContentEngine
./scripts/setup_server.sh
```

This will:
- Set up SSH keys
- Install uv
- Clone ContentEngine repo
- Install dependencies
- Check for Ollama
- Pull llama3:8b model

**⚠️ Security Note:** The `setup_server.sh` has your password in plaintext. Consider removing it after first run.

---

### Step 2: Deploy Code Updates

```bash
# Run this every time you want to push code changes
./scripts/deploy.sh
```

This will:
- Sync code to server (excluding .git, .env, venv)
- Install dependencies with `uv sync`

**⚠️ This does NOT sync .env or database!**

---

### Step 3: Configure Environment on Server

```bash
# SSH to server
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Set up .env file
cp .env.example .env
nano .env

# Add your credentials:
# - LINKEDIN_CLIENT_ID
# - LINKEDIN_CLIENT_SECRET
# - OLLAMA_HOST=http://localhost:11434
```

---

### Step 4: Set Up OAuth Tokens

**Option A: Copy from local**
```bash
# From local machine
scp ~/Work/ContentEngine/content.db ajohn@192.168.0.5:~/ContentEngine/content.db
```

**Option B: Run OAuth flow on server**
```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# This requires browser access to server
uv run python -m agents.linkedin.oauth_server

# After completing OAuth flow:
uv run python scripts/migrate_oauth.py
```

---

### Step 5: Test Deployment

```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Test 1: Context capture
uv run content-engine capture-context
# Should complete without errors

# Test 2: List posts
uv run content-engine list
# Should show database connection works

# Test 3: LinkedIn connection (dry run)
uv run content-engine draft "Test post"
uv run content-engine approve 1 --dry-run
# Should validate LinkedIn API connection
```

---

### Step 6: Set Up Background Worker

```bash
ssh ajohn@192.168.0.5

# Test worker manually first
cd ~/ContentEngine
uv run content-worker

# If successful, add to cron
crontab -e

# Add this line:
*/15 * * * * cd /home/ajohn/ContentEngine && /home/ajohn/.cargo/bin/uv run content-worker >> /tmp/content-worker.log 2>&1

# Verify cron job added
crontab -l
```

---

## Testing Checklist

After deployment, verify these work:

- [ ] **Context Capture**
  ```bash
  ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run content-engine capture-context"
  ```

- [ ] **Database Access**
  ```bash
  ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run content-engine list"
  ```

- [ ] **LinkedIn Connection** (dry-run)
  ```bash
  ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run content-engine draft 'Test' && uv run content-engine approve 1 --dry-run"
  ```

- [ ] **Ollama Access**
  ```bash
  ssh ajohn@192.168.0.5 "curl http://localhost:11434/api/tags"
  ```

- [ ] **Background Worker**
  ```bash
  ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run content-worker"
  ```

---

## Common Errors & Solutions

### Error: "Could not connect to Ollama"

**Cause:** Ollama not running or wrong host in .env

**Fix:**
```bash
ssh ajohn@192.168.0.5
systemctl start ollama
systemctl status ollama

# Update .env
cd ~/ContentEngine
nano .env
# Set: OLLAMA_HOST=http://localhost:11434
```

---

### Error: "No OAuth token found for linkedin"

**Cause:** OAuth tokens not in database

**Fix:**
```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Check if .env has tokens
cat .env | grep LINKEDIN

# Migrate tokens to database
uv run python scripts/migrate_oauth.py

# Verify
uv run content-engine list  # Should not error
```

---

### Error: "Database is locked"

**Cause:** Multiple processes accessing SQLite simultaneously

**Fix:**
```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Check for running workers
ps aux | grep content-worker

# Kill if needed
pkill -f content-worker

# Try again
uv run content-engine list
```

---

### Error: "Module not found"

**Cause:** Dependencies not installed

**Fix:**
```bash
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Reinstall dependencies
uv sync

# Verify
uv run python -c "from lib import context_capture; print('OK')"
```

---

## Rollback Plan

If deployment breaks things:

```bash
# Restore from local
scp -r ~/Work/ContentEngine/* ajohn@192.168.0.5:~/ContentEngine/

# OR restore from git
ssh ajohn@192.168.0.5
cd ~/ContentEngine
git reset --hard HEAD
git pull origin master
uv sync
```

---

## Security Considerations

**⚠️ Important:**

1. **Remove password from setup_server.sh** after first setup
   ```bash
   nano scripts/setup_server.sh
   # Remove or comment out: PASSWORD="..."
   ```

2. **Secure .env file**
   ```bash
   ssh ajohn@192.168.0.5
   chmod 600 ~/ContentEngine/.env
   ```

3. **Don't commit .env to git**
   ```bash
   # Already in .gitignore, but verify
   cat .gitignore | grep .env
   ```

4. **Use SSH keys instead of passwords**
   ```bash
   # Already done by setup_server.sh
   ```

---

## Quick Deploy (After Initial Setup)

Once everything is set up, future deployments are simple:

```bash
# From local machine
cd ~/Work/ContentEngine
./scripts/deploy.sh

# That's it! Code is synced and dependencies updated
```

No need to reconfigure .env, OAuth, or Ollama - those persist on the server.

---

## Verification Script

Create this script to verify everything works:

```bash
#!/bin/bash
# verify_deployment.sh

echo "🔍 Verifying ContentEngine deployment on 192.168.0.5..."

# Test SSH
echo -n "SSH connection: "
ssh ajohn@192.168.0.5 "echo '✅'" || echo "❌"

# Test Ollama
echo -n "Ollama service: "
ssh ajohn@192.168.0.5 "systemctl is-active ollama" | grep -q active && echo "✅" || echo "❌"

# Test uv
echo -n "uv installed: "
ssh ajohn@192.168.0.5 "command -v uv" > /dev/null && echo "✅" || echo "❌"

# Test ContentEngine imports
echo -n "Python imports: "
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run python -c 'from lib import context_capture'" && echo "✅" || echo "❌"

# Test database
echo -n "Database access: "
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && uv run content-engine list" > /dev/null && echo "✅" || echo "❌"

echo ""
echo "Deployment verification complete!"
```

---

**Last Updated:** 2026-01-14

**Server:** 192.168.0.5 (ajohn)

**Next Steps:** Review checklist, run deployment, test thoroughly
