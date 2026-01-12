# Ralph Agent Instructions - Content Engine Phase 2

## Your Task

1. Read `scripts/ralph/prd.json`
2. Read `scripts/ralph/progress.txt`
3. Read `AGENTS.md` for build/test commands
4. Check you're on the correct branch
5. Pick highest priority story where `passes: false`
6. Implement that ONE story completely
7. Run: `uv run pytest` (must pass)
8. Commit: `feat(story-id): Brief description`
9. Update prd.json: `passes: true`
10. Append learnings to progress.txt

## Tech Stack

- Python 3.11+ with uv package manager
- FastAPI (web framework)
- SQLite + aiosqlite (database)
- pytest (testing)
- Ollama (local LLM inference)
- python-dotenv (environment variables)

## Quality Gates

Before marking story complete:

1. **Tests pass:**
   ```bash
   uv run pytest
   ```

2. **Code imports without errors:**
   ```bash
   uv run python -c "from lib import context_capture"
   ```

3. **Type checking (if applicable):**
   ```bash
   uv run mypy lib/
   ```

## Progress Format

Append to `scripts/ralph/progress.txt`:

```
## [Date] - [Story ID]
- Implemented: [brief description]
- Files: [list of files]
- Tests: pytest ✓
---
```

## Codebase Patterns

**File Paths:**
- Session history: `~/.claude/History/Sessions/`
- Project notes: `~/Documents/Folio/1-Projects/`
- Use pathlib.Path for all file operations
- Always handle FileNotFoundError

**Context Capture:**
- Parse session JSONs with proper error handling
- Extract meaningful insights, not raw dumps
- Structure as clean JSON/YAML
- Store in `context/` directory

**Ollama Integration:**
- Import: `from ollama import chat`
- Model: `llama3:8b`
- Call: `chat(model='llama3:8b', messages=[{'role': 'user', 'content': prompt}])`
- Return: `response['message']['content']`
- Always handle connection errors gracefully

**Database:**
- Use aiosqlite for async operations
- Create tables on startup
- Always use `async with` for connections

## Stop Condition

If all stories in prd.json have `passes: true`:

```xml
<promise>COMPLETE</promise>
```

## Important Notes

- Use `uv run` for all Python commands
- Mock external services in tests (Ollama, file system when possible)
- Test both success and failure paths
- Include docstrings with type hints
- Follow existing code style (black, ruff)

## Error Handling

If tests fail:
1. Read the error message carefully
2. Fix the issue
3. Re-run `uv run pytest`
4. Only commit when tests pass

Do NOT mark story complete if tests fail.

## Context Capture Guidelines

Phase 2 is about building a context layer that:
1. Reads PAI session history (JSON files)
2. Reads project notes from Folio
3. Extracts meaningful insights
4. Structures cleanly for agent consumption
5. Stores for semantic blueprint agents to read

**Key principle:** Context should be structured, not raw dumps. Quality over quantity.
