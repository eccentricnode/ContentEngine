# Content Engine

Autonomous AI-powered content generation and posting system with semantic blueprints and self-improvement loops.

## Overview

Content Engine is a multi-phase AI system that:
- Captures daily context from session history and project notes
- Uses semantic blueprints to guide agent decision-making
- Generates and posts content across multiple platforms (LinkedIn, Twitter, blog)
- Learns from engagement data and self-improves

**Current Status:** Phase 2 Complete - Context Capture Layer

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Content Engine                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Phase 1: Basic Posting (CURRENT)                       │
│  ├─ LinkedIn OAuth & Posting                            │
│  ├─ Error handling & logging                            │
│  └─ Server deployment                                   │
│                                                          │
│  Phase 2: Context Capture                               │
│  ├─ Session history aggregation                         │
│  ├─ Project notes synthesis                             │
│  └─ Structured context storage                          │
│                                                          │
│  Phase 3: Semantic Blueprints                           │
│  ├─ Brand Planner blueprint                             │
│  ├─ LinkedIn Agent blueprint                            │
│  └─ Constraint-based decision logic                     │
│                                                          │
│  Phase 4-7: Autonomous agents + feedback loops          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Technical Stack

- **Language:** Python 3.11+
- **Package Manager:** uv (fast, modern Python tooling)
- **AI Integration:** Anthropic Claude, OpenAI, Local LLMs (Ollama)
- **Deployment:** Self-hosted on local server (192.168.0.5)
- **Testing:** pytest
- **Code Quality:** black, ruff, mypy

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- LinkedIn Developer account (for API access)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd ContentEngine

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### LinkedIn OAuth Setup

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Create a new app
3. Enable "Share on LinkedIn" and "OpenID Connect" products
4. Set redirect URI to `http://localhost:3000/callback`
5. Copy Client ID and Client Secret to `.env`
6. Run OAuth flow:

```bash
uv run linkedin-oauth
```

7. Open browser to `http://localhost:3000`
8. Authorize the app
9. Save the access token to `.env`

### First-Time Setup

After OAuth flow, migrate your token to the database:

```bash
uv run python scripts/migrate_oauth.py
```

### Database Setup

ContentEngine uses Alembic for database migrations.

**Initialize database:**

```bash
# First time only - create database with latest schema
uv run alembic upgrade head
```

**Check migration status:**

```bash
uv run alembic current
```

See [DATABASE.md](DATABASE.md) for detailed migration guide.

### Usage

**Context Capture (Phase 2):**

```bash
# Capture daily context from sessions and projects
uv run content-engine capture-context

# Capture context for specific date
uv run content-engine capture-context --date 2026-01-12

# Custom directories
uv run content-engine capture-context \
  --sessions-dir ~/.claude/History/Sessions/ \
  --projects-dir ~/Documents/Folio/1-Projects/ \
  --output-dir context/

# View captured context
cat context/2026-01-12.json
```

Context capture automatically:
1. Reads PAI session history (JSON/JSONL files)
2. Reads project notes from Folio (Markdown with frontmatter)
3. Synthesizes with local LLM (Ollama llama3:8b)
4. Extracts themes, decisions, and progress
5. Saves structured JSON to `context/YYYY-MM-DD.json`

**Prerequisites for context capture:**
- Ollama installed and running (`ollama serve`)
- llama3:8b model pulled (`ollama pull llama3:8b`)
- Session history at `~/.claude/History/Sessions/` (optional)
- Project notes at `~/Documents/Folio/1-Projects/` (optional)

**LinkedIn Analytics Collection:**

```bash
# Collect analytics for all recent posts (last 7 days)
uv run content-engine collect-analytics

# Collect analytics for posts from last 14 days
uv run content-engine collect-analytics --days-back 14

# Test analytics for a single post
uv run content-engine collect-analytics --test-post urn:li:share:7412668096475369472
```

Analytics collection automatically:
1. Loads LinkedIn access token from environment (`LINKEDIN_ACCESS_TOKEN`) or database
2. Fetches post metrics (impressions, likes, comments, shares, clicks, engagement rate)
3. Updates `data/posts.jsonl` with fresh analytics
4. Skips posts that already have metrics

**Prerequisites for analytics collection:**
- LinkedIn access token with analytics permissions
- Set `LINKEDIN_ACCESS_TOKEN` environment variable OR store token in database
- `data/posts.jsonl` file (create with `mkdir -p data && touch data/posts.jsonl`)

**posts.jsonl Schema:**

Each line in `data/posts.jsonl` is a JSON object representing a single LinkedIn post:

```json
{
  "post_id": "urn:li:share:7412668096475369472",
  "posted_at": "2026-01-01T00:00:00",
  "blueprint_version": "manual_v1",
  "content": "Your post content here",
  "metrics": {
    "post_id": "urn:li:share:7412668096475369472",
    "impressions": 1234,
    "likes": 45,
    "comments": 3,
    "shares": 2,
    "clicks": 67,
    "engagement_rate": 0.0405,
    "fetched_at": "2026-01-17T10:30:00"
  }
}
```

**Fields:**
- `post_id` (string): LinkedIn share URN (e.g., "urn:li:share:7412668096475369472")
- `posted_at` (string): ISO 8601 timestamp when post was published
- `blueprint_version` (string): Content framework version used (e.g., "manual_v1", "STF_v1")
- `content` (string): Full text content of the post
- `metrics` (object, optional): Analytics data (populated after running collect-analytics)
  - `post_id` (string): Same as parent post_id
  - `impressions` (int): Number of times post was shown
  - `likes` (int): Number of likes/reactions
  - `comments` (int): Number of comments
  - `shares` (int): Number of shares/reposts
  - `clicks` (int): Number of clicks on post links
  - `engagement_rate` (float): Calculated as (likes + comments + shares) / impressions
  - `fetched_at` (string): ISO 8601 timestamp when metrics were fetched

**Example: Adding a post manually**

```bash
# Add a new post to posts.jsonl (without metrics initially)
echo '{"post_id": "urn:li:share:7412668096475369472", "posted_at": "2026-01-01T00:00:00", "blueprint_version": "manual_v1", "content": "New Year 2026 post"}' >> data/posts.jsonl

# Fetch analytics for the post
uv run content-engine collect-analytics --test-post urn:li:share:7412668096475369472

# Or fetch analytics for all recent posts
uv run content-engine collect-analytics
```

**Content Engine CLI:**

```bash
# Create a draft post
uv run content-engine draft "Your post content here"

# List all posts
uv run content-engine list

# List only drafts
uv run content-engine list --status draft

# Show full post details
uv run content-engine show 1

# Approve and post immediately
uv run content-engine approve 1

# Dry run (test without posting)
uv run content-engine approve 1 --dry-run

# Schedule for later
uv run content-engine schedule 1 "2024-01-15 09:00"

# Reject a draft
uv run content-engine reject 1
```

**Background Worker (for scheduled posts):**

```bash
# Run once to process scheduled posts
uv run content-worker

# Set up cron job (runs every 15 minutes)
crontab -e
# Add: */15 * * * * cd /path/to/ContentEngine && uv run content-worker >> /tmp/content-worker.log 2>&1
```

**Direct LinkedIn API (for testing):**

```bash
# Test connection
uv run python -m agents.linkedin.test_connection

# Post directly (bypasses database)
uv run python -m agents.linkedin.post "Your content here"
```

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy agents/

# Code formatting
uv run black .
uv run ruff check .
```

## Deployment

Deploy to server at `192.168.0.5`:

```bash
./scripts/deploy.sh
```

## Roadmap

- [x] Phase 1: LinkedIn OAuth & posting infrastructure
- [x] Phase 1.5: Database, CLI, and scheduled posting
- [x] Phase 2: Context capture from session history (COMPLETE)
  - [x] Session history parser (CE-001)
  - [x] Project notes aggregator (CE-002)
  - [x] Context synthesizer with Ollama (CE-003)
  - [x] Context storage and CLI (CE-004)
- [ ] Phase 3: Semantic blueprint architecture (NEXT)
- [ ] Phase 4: Brand Planner agent
- [ ] Phase 5: Autonomous content generation
- [ ] Phase 6: Engagement feedback loops
- [ ] Phase 7: Multi-platform support (Twitter, blog, YouTube)

## Interview Demo Points

This project demonstrates:

- **AI System Architecture:** Multi-agent system with semantic blueprints
- **OAuth Implementation:** Secure LinkedIn API integration
- **Production Infrastructure:** Error handling, logging, deployment automation
- **Self-Improving Systems:** Engagement feedback loops (Phase 6)
- **Full Stack:** OAuth server, API integration, agent orchestration

Built in Python for superior AI/ML library ecosystem (LangChain, LlamaIndex, Anthropic SDK).

## License

MIT

## Author

Austin Johnson - AI Engineer
