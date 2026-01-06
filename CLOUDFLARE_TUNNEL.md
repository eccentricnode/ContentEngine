# Cloudflare Tunnel Setup Guide

**Expose `demo.theaustinjohnson.com` to your local Content Engine web UI**

---

## What is Cloudflare Tunnel?

Cloudflare Tunnel creates a secure connection from your local machine to Cloudflare's network without:
- ❌ Opening ports on your router
- ❌ Exposing your public IP
- ❌ Complex networking configuration

✅ **Result:** `demo.theaustinjohnson.com` routes to `localhost:5000` securely

---

## Prerequisites

- Cloudflare account (free)
- Domain `theaustinjohnson.com` managed by Cloudflare
- Content Engine running locally
- Linux machine (your dev machine or server at 192.168.0.5)

---

## Step 1: Install Cloudflared

```bash
# Download cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared

# Make executable
chmod +x cloudflared

# Move to system path
sudo mv cloudflared /usr/local/bin/

# Verify installation
cloudflared --version
```

---

## Step 2: Authenticate with Cloudflare

```bash
# Login to Cloudflare (opens browser)
cloudflared tunnel login
```

**What happens:**
1. Browser opens to Cloudflare login
2. Select `theaustinjohnson.com` domain
3. Authorize cloudflared
4. Certificate saved to `~/.cloudflared/cert.pem`

---

## Step 3: Create a Tunnel

```bash
# Create tunnel named 'content-engine'
cloudflared tunnel create content-engine
```

**Output:**
```
Tunnel credentials written to /home/user/.cloudflared/<TUNNEL_ID>.json
Created tunnel content-engine with id <TUNNEL_ID>
```

**Save the Tunnel ID** - you'll need it.

---

## Step 4: Configure the Tunnel

Create configuration file:

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

**Add this content:**

```yaml
tunnel: <TUNNEL_ID>  # Replace with your tunnel ID from Step 3
credentials-file: /home/user/.cloudflared/<TUNNEL_ID>.json  # Replace with your path

ingress:
  - hostname: demo.theaustinjohnson.com
    service: http://localhost:5000
  - service: http_status:404
```

**Important:**
- Replace `<TUNNEL_ID>` with your actual tunnel ID
- Replace `/home/user/` with your actual home directory path
- The `ingress` section routes `demo.theaustinjohnson.com` → `localhost:5000`

---

## Step 5: Create DNS Record

Route the subdomain to your tunnel:

```bash
cloudflared tunnel route dns content-engine demo.theaustinjohnson.com
```

**Output:**
```
Created CNAME record demo.theaustinjohnson.com which will route to this tunnel
```

**What this does:**
- Creates a CNAME record in Cloudflare DNS
- Points `demo.theaustinjohnson.com` → Cloudflare edge → Your tunnel

**Verify in Cloudflare Dashboard:**
1. Go to https://dash.cloudflare.com
2. Select `theaustinjohnson.com` domain
3. DNS → Records
4. You should see: `demo` CNAME pointing to `<TUNNEL_ID>.cfargotunnel.com`

---

## Step 6: Start Content Engine

**On your machine (or 192.168.0.5):**

```bash
cd ~/Work/ContentEngine

# Start the web UI
uv run python web/app.py
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:5000
```

**Keep this running in one terminal.**

---

## Step 7: Start the Tunnel

**In a new terminal:**

```bash
cloudflared tunnel run content-engine
```

**Expected output:**
```
2024-01-06 Your free tunnel has started!
Visit https://demo.theaustinjohnson.com
```

**Keep this running.**

---

## Step 8: Test the Demo

Open browser to:
- https://demo.theaustinjohnson.com

You should see:
- ✅ Content Engine dashboard
- ✅ Demo banner at top
- ✅ Stats cards
- ✅ Recent posts (if any exist)

---

## Step 9: Run as Background Service (Optional)

**To keep tunnel running permanently:**

### Option A: Systemd Service (Recommended)

```bash
# Install tunnel as a service
sudo cloudflared service install

# Start the service
sudo systemctl start cloudflared

# Enable on boot
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

### Option B: Screen/tmux

```bash
# Create screen session
screen -S tunnel

# Run tunnel
cloudflared tunnel run content-engine

# Detach: Ctrl+A, then D
# Reattach: screen -r tunnel
```

---

## Full Workflow (After Setup)

**Daily usage:**

```bash
# Start Content Engine web UI
cd ~/Work/ContentEngine
uv run python web/app.py &

# Tunnel runs automatically (if using systemd)
# Or manually: cloudflared tunnel run content-engine &

# Visit: https://demo.theaustinjohnson.com
```

---

## Troubleshooting

### "Tunnel not found"
```bash
# List tunnels
cloudflared tunnel list

# If missing, recreate:
cloudflared tunnel create content-engine
```

### "Connection refused" when visiting demo.theaustinjohnson.com
```bash
# Check web UI is running
curl http://localhost:5000

# If not running:
cd ~/Work/ContentEngine
uv run python web/app.py
```

### "DNS record not found"
```bash
# Re-create DNS route
cloudflared tunnel route dns content-engine demo.theaustinjohnson.com

# Or manually add in Cloudflare Dashboard:
# Type: CNAME
# Name: demo
# Target: <TUNNEL_ID>.cfargotunnel.com
```

### Tunnel logs
```bash
# If using systemd
sudo journalctl -u cloudflared -f

# If running manually
# Logs appear in terminal where cloudflared is running
```

---

## Security Notes

**This is secure because:**
- ✅ No ports opened on your router
- ✅ Cloudflare handles TLS (HTTPS automatic)
- ✅ Your IP address is hidden
- ✅ Only specified hostnames work (demo.theaustinjohnson.com)

**Demo-only features:**
- All action buttons are disabled
- Demo banner explains it's read-only
- No user data can be modified by visitors
- Derek can browse, but not approve/delete posts

---

## For Loom Video

**Before recording:**
1. Start Content Engine web UI
2. Start Cloudflare Tunnel
3. Verify https://demo.theaustinjohnson.com works
4. Create 2-3 draft posts using CLI (so there's data to show)
5. Record Loom showing both CLI usage AND web UI

**In the Loom:**
- Show CLI creating draft: `content-engine draft "Test post"`
- Switch to browser: https://demo.theaustinjohnson.com
- Show the draft appearing in UI
- Hover over disabled buttons (show the tooltip)
- Explain: "This is live, but buttons are disabled for demo purposes"

---

## Cleanup (if needed)

```bash
# Stop tunnel service
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared

# Delete tunnel
cloudflared tunnel delete content-engine

# Remove DNS record
# Go to Cloudflare Dashboard → DNS → Delete demo record
```

---

## Quick Reference

```bash
# Create tunnel
cloudflared tunnel create content-engine

# Configure tunnel
nano ~/.cloudflared/config.yml

# Route DNS
cloudflared tunnel route dns content-engine demo.theaustinjohnson.com

# Run tunnel
cloudflared tunnel run content-engine

# Install as service
sudo cloudflared service install

# Check tunnel status
cloudflared tunnel info content-engine
```

---

**Questions?**
- Cloudflare Tunnel Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare Dashboard: https://dash.cloudflare.com
