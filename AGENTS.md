# Content Engine - Build Commands

## Test Commands

### Run All Tests
```bash
uv run pytest
```

### Run Specific Test
```bash
uv run pytest tests/test_context_capture.py -v
```

### Run with Coverage
```bash
uv run pytest --cov=lib --cov-report=term-missing
```

## Manual Testing

### Test Context Capture
```bash
uv run content-engine capture-context
```

### Test Ollama Connection
```bash
uv run python -c "from ollama import chat; print(chat(model='llama3:8b', messages=[{'role': 'user', 'content': 'Hello'}]))"
```

## Codebase Patterns

**Package Manager:**
- Always use `uv run` prefix for Python commands
- Install dependencies: `uv add package-name`
- Sync dependencies: `uv sync`

**File Paths:**
- Session history: `~/.claude/History/Sessions/`
- Project notes: `~/Documents/Folio/1-Projects/`
- Context storage: `context/YYYY-MM-DD.json`
- Always use `pathlib.Path` and `os.path.expanduser()`

**Context Capture:**
- Read session JSONs with error handling
- Parse markdown with frontmatter support
- Structure as clean dataclasses/TypedDict
- Quality over quantity - extract insights, not dumps

**Ollama Integration:**
- Import: `from ollama import chat`
- Model: `llama3:8b` (already pulled locally)
- Call: `chat(model='llama3:8b', messages=[{'role': 'user', 'content': prompt}])`
- Return: `response['message']['content']`
- Handle connection errors: OllamaConnectionError

**Database:**
- Use aiosqlite for async operations
- Tables already exist: posts, linkedin_tokens
- Create new tables as needed for context storage

**Testing:**
- Mock external dependencies (Ollama, file system)
- Use pytest fixtures for test data
- Test both success and failure paths

## Common Gotchas

**uv not found:**
- Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Restart shell after install

**Ollama not running:**
- Check: `ps aux | grep ollama`
- Start: `ollama serve` (or systemd service)
- Pull model: `ollama pull llama3:8b`

**Session history missing:**
- Check path: `ls ~/.claude/History/Sessions/`
- Session files may be .json or .jsonl
- Handle both formats

**Import errors:**
- Sync dependencies: `uv sync`
- Check pyproject.toml for missing packages
