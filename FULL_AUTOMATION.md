# ContentEngine - Full Automation Setup

## Current State vs Fully Automatic

### What's Automatic NOW (After CI/CD Setup):
- ✅ Code deployment (push to GitHub → deploys to server)
- ✅ Scheduled post publishing (background worker runs 24/7)
- ✅ Service auto-restart (on deploy or reboot)

### What Still Needs Manual Trigger:
- ❌ Context capture (you run the command daily)
- ❌ Content generation (Phase 5 - not built yet)
- ❌ Draft creation (manual or via Phase 5)

### What FULLY AUTOMATIC Looks Like:
```
Daily at 11:59 PM:
1. Capture context from your day's work → JSON file
2. Generate content ideas from context → Database
3. Create LinkedIn posts → Drafts in database
4. Auto-schedule for optimal times → Scheduled posts
5. Background worker publishes → LinkedIn

You just wake up and check what it posted.
```

---

## Option 1: Automatic Context Capture (Easy)

**Goal:** Capture context automatically every day at 11:59 PM

### Setup Steps

```bash
# 1. SSH to server
ssh ajohn@192.168.0.5

# 2. Copy timer files
cd ~/ContentEngine
mkdir -p ~/.config/systemd/user

cp systemd/content-engine-capture.service ~/.config/systemd/user/
cp systemd/content-engine-capture.timer ~/.config/systemd/user/

# 3. Update paths if needed (if deploy path is different)
sed -i 's|/home/ajohn/ContentEngine|'$HOME'/ContentEngine|g' ~/.config/systemd/user/content-engine-capture.service

# 4. Enable and start timer
systemctl --user daemon-reload
systemctl --user enable content-engine-capture.timer
systemctl --user start content-engine-capture.timer

# 5. Verify it's scheduled
systemctl --user list-timers

# You should see:
# NEXT                         LEFT          LAST  PASSED  UNIT
# Today 23:59:00              Xh Xmin left   -     -       content-engine-capture.timer
```

### Test It

```bash
# Trigger manually to test
systemctl --user start content-engine-capture.service

# Check logs
journalctl --user -u content-engine-capture.service -f

# View captured context
cat ~/ContentEngine/context/$(date +%Y-%m-%d).json
```

**Now context captures automatically every night!**

---

## Option 2: Pull Data Dashboard (View What's Running)

**Goal:** Web dashboard to see what the system is doing

### Quick Status Script

Create a script to check system status:

```bash
# Create status check script
cat > ~/ContentEngine/scripts/status.sh << 'EOF'
#!/bin/bash

echo "📊 ContentEngine Status"
echo "======================="
echo ""

# Context Capture
echo "📅 Context Capture:"
latest_context=$(ls -t ~/ContentEngine/context/*.json 2>/dev/null | head -1)
if [ -n "$latest_context" ]; then
    echo "   Latest: $(basename $latest_context)"
    echo "   Size: $(du -h $latest_context | cut -f1)"
else
    echo "   No context captured yet"
fi
echo ""

# Database Stats
echo "📊 Database Stats:"
cd ~/ContentEngine
uv run python << 'PYTHON'
from lib.database import get_db, Post, PostStatus
db = get_db()
total = db.query(Post).count()
drafted = db.query(Post).filter(Post.status == PostStatus.DRAFT).count()
scheduled = db.query(Post).filter(Post.status == PostStatus.SCHEDULED).count()
posted = db.query(Post).filter(Post.status == PostStatus.POSTED).count()
print(f"   Total Posts: {total}")
print(f"   Drafts: {drafted}")
print(f"   Scheduled: {scheduled}")
print(f"   Posted: {posted}")
db.close()
PYTHON
echo ""

# Services
echo "🔧 Services:"
systemctl --user is-active content-engine-worker.service > /dev/null 2>&1 && \
    echo "   Worker: ✅ Running" || echo "   Worker: ❌ Stopped"

systemctl --user is-active content-engine-capture.timer > /dev/null 2>&1 && \
    echo "   Context Timer: ✅ Active" || echo "   Context Timer: ❌ Inactive"

systemctl is-active ollama.service > /dev/null 2>&1 && \
    echo "   Ollama: ✅ Running" || echo "   Ollama: ❌ Stopped"
echo ""

# Next scheduled capture
echo "⏰ Next Context Capture:"
systemctl --user list-timers --no-pager | grep content-engine-capture | awk '{print "   "$1, $2, $3}'
echo ""

# Recent activity
echo "📝 Recent Activity (last 5 posts):"
cd ~/ContentEngine
uv run content-engine list --limit 5
EOF

chmod +x ~/ContentEngine/scripts/status.sh
```

### Use It

```bash
# From your local machine
ssh ajohn@192.168.0.5 "~/ContentEngine/scripts/status.sh"

# Output:
# 📊 ContentEngine Status
# =======================
#
# 📅 Context Capture:
#    Latest: 2026-01-14.json
#    Size: 12K
#
# 📊 Database Stats:
#    Total Posts: 42
#    Drafts: 3
#    Scheduled: 2
#    Posted: 37
#
# 🔧 Services:
#    Worker: ✅ Running
#    Context Timer: ✅ Active
#    Ollama: ✅ Running
#
# ⏰ Next Context Capture:
#    Today 23:59:00 4h 23min left
```

---

## Option 3: Fetch Data to Local Machine

**Goal:** Pull captured context and posts to your local machine for review

### Sync Script

```bash
# Create local sync script
cat > ~/Work/ContentEngine/scripts/pull_data.sh << 'EOF'
#!/bin/bash

SERVER="ajohn@192.168.0.5"
SERVER_PATH="/home/ajohn/ContentEngine"
LOCAL_PATH="$HOME/Work/ContentEngine"

echo "📥 Pulling data from server..."

# Pull context files
echo "  → Context files..."
rsync -avz $SERVER:$SERVER_PATH/context/ $LOCAL_PATH/context/

# Pull database (for local inspection)
echo "  → Database..."
rsync -avz $SERVER:$SERVER_PATH/content.db $LOCAL_PATH/content.db.server

# Pull logs
echo "  → Logs..."
rsync -avz $SERVER:$SERVER_PATH/*.log $LOCAL_PATH/logs/

echo "✅ Data pulled successfully!"
echo ""
echo "View context: ls -lh $LOCAL_PATH/context/"
echo "View database: sqlite3 $LOCAL_PATH/content.db.server"
echo "View logs: ls -lh $LOCAL_PATH/logs/"
EOF

chmod +x ~/Work/ContentEngine/scripts/pull_data.sh
```

### Use It

```bash
cd ~/Work/ContentEngine

# Pull latest data
./scripts/pull_data.sh

# View latest context
cat context/$(date +%Y-%m-%d).json | jq .

# View posts locally
uv run content-engine list --limit 10

# View worker logs
tail -f logs/worker.log
```

---

## Option 4: Simple Web Dashboard (Advanced)

**Goal:** Web interface to see what the system is doing

### Flask Dashboard (Quick & Simple)

```python
# ~/ContentEngine/web/dashboard.py
from flask import Flask, render_template_string
from lib.database import get_db, Post, PostStatus
from datetime import datetime
import os
import json

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ContentEngine Dashboard</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a1a; color: #fff; }
        .card { background: #2a2a2a; padding: 20px; margin: 10px 0; border-radius: 8px; }
        .status { display: inline-block; padding: 5px 10px; border-radius: 4px; margin: 5px; }
        .running { background: #2ecc71; }
        .stopped { background: #e74c3c; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; }
    </style>
</head>
<body>
    <h1>📊 ContentEngine Dashboard</h1>

    <div class="card">
        <h2>System Status</h2>
        <span class="status running">Worker: Running</span>
        <span class="status running">Ollama: Running</span>
        <span class="status running">Capture: Active</span>
    </div>

    <div class="card">
        <h2>Database Stats</h2>
        <p>Total Posts: {{ stats.total }}</p>
        <p>Drafts: {{ stats.drafts }}</p>
        <p>Scheduled: {{ stats.scheduled }}</p>
        <p>Posted: {{ stats.posted }}</p>
    </div>

    <div class="card">
        <h2>Recent Context</h2>
        <p>Latest: {{ context.date }}</p>
        <p>Themes: {{ context.themes|length }}</p>
        <p>Decisions: {{ context.decisions|length }}</p>
    </div>

    <div class="card">
        <h2>Recent Posts</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Created</th>
                <th>Content</th>
            </tr>
            {% for post in posts %}
            <tr>
                <td>{{ post.id }}</td>
                <td>{{ post.status.value }}</td>
                <td>{{ post.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                <td>{{ post.content[:80] }}...</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    db = get_db()

    # Database stats
    stats = {
        'total': db.query(Post).count(),
        'drafts': db.query(Post).filter(Post.status == PostStatus.DRAFT).count(),
        'scheduled': db.query(Post).filter(Post.status == PostStatus.SCHEDULED).count(),
        'posted': db.query(Post).filter(Post.status == PostStatus.POSTED).count(),
    }

    # Recent posts
    posts = db.query(Post).order_by(Post.created_at.desc()).limit(10).all()

    # Latest context
    context_dir = 'context'
    context_files = sorted([f for f in os.listdir(context_dir) if f.endswith('.json')], reverse=True)
    context = {'date': 'None', 'themes': [], 'decisions': []}
    if context_files:
        with open(os.path.join(context_dir, context_files[0])) as f:
            context_data = json.load(f)
            context = {
                'date': context_files[0].replace('.json', ''),
                'themes': context_data.get('themes', []),
                'decisions': context_data.get('decisions', [])
            }

    db.close()

    return render_template_string(DASHBOARD_HTML, stats=stats, posts=posts, context=context)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Run Dashboard

```bash
# On server
ssh ajohn@192.168.0.5
cd ~/ContentEngine

# Install flask
uv add flask

# Run dashboard
uv run python web/dashboard.py

# Access from browser:
# http://192.168.0.5:5000
```

---

## What You Actually Need

Based on your question "I just need to pull the data," here's the simplest approach:

### 1. Set Up Automatic Context Capture
```bash
# Run once on server
ssh ajohn@192.168.0.5 "cd ~/ContentEngine && \
  cp systemd/content-engine-capture.* ~/.config/systemd/user/ && \
  systemctl --user daemon-reload && \
  systemctl --user enable --now content-engine-capture.timer"
```

### 2. Use the Status Check
```bash
# Add this alias to your ~/.zshrc
alias ce-status='ssh ajohn@192.168.0.5 "~/ContentEngine/scripts/status.sh"'

# Then just run:
ce-status
```

### 3. Pull Data When Needed
```bash
# Add this alias too
alias ce-pull='cd ~/Work/ContentEngine && ./scripts/pull_data.sh'

# Then run:
ce-pull
```

**That's it!** The system runs on its own, you just check status and pull data when you want to see what happened.

---

## Future: True Full Automation (Phase 5)

What's still missing for **zero manual intervention:**

```
Phase 5: Autonomous Content Generation
├── Read daily context (automatic ✅)
├── Generate content ideas from context (needs building ❌)
├── Create LinkedIn posts (needs building ❌)
├── Schedule at optimal times (needs building ❌)
└── Publish automatically (automatic ✅)
```

Once Phase 5 is built:
1. You work on projects (captured automatically)
2. System generates content from your work (automatic)
3. System posts to LinkedIn (automatic)
4. You just review analytics

**For now:** The infrastructure runs automatically, you just need to trigger content generation manually or wait for Phase 5.

---

**Want me to set up the automatic context capture and pull scripts for you?**
