# Content Engine

Autonomous content pipeline that captures what I'm working on, generates posts across platforms, and learns from what actually performs.

I built this because I was spending 20 minutes per LinkedIn post doing the same thing every time — pulling context from session notes, structuring it against my voice, posting, then never looking at what worked. That's a system, not a creative act. So I automated the system and kept the creative part.

## What it does

- **Captures daily context** from my Claude Code session history and project notes — what I shipped, what I learned, what failed
- **Generates content** using semantic blueprints that encode my voice, brand constraints, and platform rules
- **Posts to LinkedIn** via OAuth with draft review, scheduling, and approval gates — nothing goes out without my sign-off
- **Tracks engagement** and feeds performance data back into the pipeline so the system learns what lands

**Current status:** Phase 3 complete (26/26 stories). Semantic blueprints, multi-agent validation, and content generation all working. Feedback loops (Phase 6) are next.

## Architecture

```
Context Capture  →  Blueprint Engine  →  Multi-Agent Pipeline  →  Platform Posting
(sessions, notes)   (STF, MRS, SLA, PIF)  (generate → validate → refine)  (LinkedIn, drafts, scheduling)
                                                    ↑                              │
                                                    └──── engagement feedback ─────┘
```

The pipeline uses a **Generator → Validator → Refiner** pattern. Llama drafts, Claude validates against brand constraints, refinement happens in-loop. Blueprints aren't prompts — they're structured decision frameworks that encode what makes a post *mine* vs. generic AI slop.

## Tech stack

- **Python 3.11+** with **uv** for package management
- **AI:** Ollama locally (llama3:8b, free) → AWS Bedrock in production (Claude Haiku + Llama 3.3 70B, ~$0.004/post)
- **Database:** SQLite dev → PostgreSQL production, Alembic migrations
- **Testing:** 403 tests passing, ruff compliant, mypy typed
- **Deployment:** Self-hosted, `./scripts/deploy.sh`

## Quick start

```bash
git clone <repo-url> && cd ContentEngine
uv sync
cp .env.example .env   # add LinkedIn credentials
uv run alembic upgrade head
uv run content-engine capture-context
uv run content-engine generate --pillar what_building --framework STF
```

## Key commands

```bash
# Context capture
uv run content-engine capture-context              # today's context from sessions + notes
uv run content-engine capture-context --date 2026-01-12

# Content generation
uv run content-engine blueprints list              # available frameworks
uv run content-engine generate --pillar what_building --framework STF
uv run content-engine sunday-power-hour            # batch workflow for the week

# Post management
uv run content-engine draft "Your content here"
uv run content-engine approve 1                    # review then post
uv run content-engine approve 1 --dry-run          # test without posting

# Analytics
uv run content-engine collect-analytics
python scripts/analytics_dashboard.py
```

## Roadmap

- [x] Phase 1: LinkedIn OAuth + posting infrastructure
- [x] Phase 1.5: Database, CLI, scheduled posting
- [x] Phase 2: Context capture from session history
- [x] Phase 3: Semantic blueprints (26/26 stories)
- [ ] Phase 4: Brand Planner agent
- [ ] Phase 5: Autonomous content generation
- [ ] Phase 6: Engagement feedback loops
- [ ] Phase 7: Multi-platform (Twitter, blog, YouTube)

## Cost

Running the full pipeline on AWS Bedrock: **< $1.50/year** for 30 posts/month. Local dev with Ollama is free.

## License

MIT
