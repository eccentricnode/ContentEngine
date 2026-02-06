# Ralph Agent Instructions - Content Engine Phase 3

## Your Task

You are implementing **Phase 3: Semantic Blueprints** for Content Engine, a Python-based autonomous content generation system.

**Goal:** Build a blueprint system that encodes content frameworks (STF, MRS, SLA, PIF), workflows (Sunday Power Hour), and brand constraints as YAML files, with validation and content generation capabilities.

## Workflow

1. Read `scripts/ralph/prd.json` - See all user stories
2. Read `scripts/ralph/progress.txt` - Check patterns and learnings
3. Read `AGENTS.md` - Build/test commands
4. Check you're on the correct branch (from prd.json branchName)
5. Pick highest priority story where `passes: false`
6. Implement that ONE story completely (don't skip ahead)
7. Run quality checks (mypy, ruff, pytest - ALL must pass)
8. Commit with message: `feat(story-id): Brief description`
9. Update prd.json: set `passes: true` for completed story
10. Append learnings to progress.txt (patterns discovered, gotchas, best practices)
11. Loop continues automatically

## Tech Stack

- **Language:** Python 3.11+
- **Package Manager:** uv (NOT pip) - Use `uv add` to install dependencies
- **Testing:** pytest
- **Type Checking:** mypy
- **Linting:** ruff
- **Database:** SQLAlchemy ORM (SQLite for MVP)
- **YAML:** PyYAML for blueprint parsing
- **Templates:** pybars3 or chevron for Handlebars rendering

## Quality Gates (ALL must pass before commit)

```bash
# 1. Type check
uv run mypy lib/ agents/

# 2. Linting  
uv run ruff check .

# 3. Tests
uv run pytest
```

**If any fail:** Fix them before committing. Never commit broken code.

## New Dependencies

When you need to add dependencies:

```bash
# Add to project
uv add pybars3  # or chevron, whichever you choose for Handlebars

uv add PyYAML   # if not already present

# Sync environment
uv sync
```

## Architecture Context

**Existing Phase 2 (Context Capture) integration:**
- `lib/context_synthesizer.py` - Extracts themes/decisions/progress from session history
- Use `synthesize_daily_context()` to get DailyContext for blueprint prompts

**New Phase 3 components you're building:**
- `blueprints/` - YAML files defining frameworks, workflows, constraints
- `lib/blueprint_loader.py` - Load and cache blueprints
- `lib/blueprint_engine.py` - Validation and workflow execution
- `lib/template_renderer.py` - Handlebars template rendering
- `agents/linkedin/content_generator.py` - Generate posts using blueprints
- `agents/linkedin/post_validator.py` - Validate posts against constraints

## Blueprint YAML Structure Examples

**Framework (STF.yaml):**
```yaml
name: STF
platform: linkedin
description: Storytelling Framework
structure:
  sections:
    - Problem
    - Tried
    - Worked
    - Lesson
validation:
  min_sections: 4
  min_chars: 600
  max_chars: 1500
compatible_pillars:
  - what_building
  - what_learning
  - problem_solution
```

**Constraint (BrandVoice.yaml):**
```yaml
name: BrandVoice
type: constraint
characteristics:
  - technical_but_accessible
  - authentic
  - confident
forbidden_phrases:
  - "leverage synergy"
  - "disrupt the market"
  - "hustle culture"
validation_rules:
  specificity: high
  actionability: required
```

## Progress Format

After completing each story, APPEND to `scripts/ralph/progress.txt`:

```
## [YYYY-MM-DD] - [Story ID] - [Story Title]

**Implemented:**
- Brief description of what was built

**Files changed:**
- path/to/file1.py
- path/to/file2.py

**Learnings:**
- Pattern discovered (add to Codebase Patterns section)
- Gotcha encountered
- Best practice identified

**Tests:**
- mypy: PASS
- ruff: PASS
- pytest: PASS

**Commit:** <commit hash>

---
```

## Stop Condition

When ALL stories in prd.json have `passes: true`:

```xml
<promise>COMPLETE</promise>
```

Otherwise, continue to next iteration.

## Important Notes

- **Follow existing patterns:** Check how `lib/database.py`, `lib/context_synthesizer.py` are structured
- **Type hints everywhere:** mypy strict mode
- **Mock external dependencies:** Don't call real APIs in tests
- **Read the plan:** The master plan is in this prompt's context - follow the architecture described there
- **One story at a time:** Don't try to implement multiple stories at once
- **Ask questions in commits:** If design decision needed, make reasonable choice and document in commit message

## Error Handling

If quality checks fail:
1. Read error message carefully
2. Fix the issue
3. Re-run ALL quality checks
4. Only commit when everything passes

Do NOT mark story as complete if tests/typing/linting fail.

## Integration Points

**With Phase 2 (Context Capture):**
- Import `synthesize_daily_context()` from `lib/context_synthesizer.py`
- Use DailyContext (themes, decisions, progress) as input to blueprint prompts

**With CLI:**
- Add commands to `cli.py` following existing patterns (Click groups/commands)
- Test CLI commands work: `uv run content-engine <command>`

**With Database:**
- Add new models to `lib/database.py` (Blueprint, ContentPlan tables)
- Create migrations if needed: `alembic revision --autogenerate -m "message"`
- Run migrations: `alembic upgrade head`

## Testing Strategy

**Unit tests:**
- Test blueprint loading/parsing
- Test validation logic
- Test template rendering
- Mock file system, LLM calls, database

**Integration tests:**
- Test end-to-end content generation
- Test workflow execution
- Use real YAML files but mocked LLM

## Current Codebase Patterns (from AGENTS.md)

**Package Manager:**
- Always use `uv run` prefix
- Install: `uv add package-name`
- Sync: `uv sync`

**File Paths:**
- Use `pathlib.Path` and `os.path.expanduser()`
- Session history: `~/.claude/History/Sessions/`
- Project notes: `~/Documents/Folio/1-Projects/`

**Database:**
- Use aiosqlite for async operations
- Models in `lib/database.py`
- Use context managers for sessions

**Testing:**
- pytest fixtures for test data
- Mock external dependencies
- Test success and failure paths

---

**Start with the highest priority story in prd.json and build one story at a time. Good luck, Ralph! 🚀**
