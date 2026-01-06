# Content Engine

Autonomous AI-powered content generation and posting system with semantic blueprints and self-improvement loops.

## Overview

Content Engine is a multi-phase AI system that:
- Captures daily context from session history and project notes
- Uses semantic blueprints to guide agent decision-making
- Generates and posts content across multiple platforms (LinkedIn, Twitter, blog)
- Learns from engagement data and self-improves

**Current Status:** Phase 1 - Basic posting infrastructure

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

### Usage

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
- [x] Phase 1.5: Database, CLI, and scheduled posting (CURRENT)
- [ ] Phase 2: Context capture from session history
- [ ] Phase 3: Semantic blueprint architecture
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
