# Ralph PRD Management

This directory contains multiple PRD files for different Ralph workflows.

## Available PRDs

| PRD File | Purpose | Status |
|----------|---------|--------|
| `prd.json` | **ACTIVE** - Currently loaded PRD | - |
| `context-capture-prd.json` | Context capture from PAI sessions | ✅ Complete (all stories pass) |
| `analytics-prd.json` | LinkedIn analytics integration | 🟡 Ready to run |

## Switching PRDs

Ralph always reads `prd.json`. To switch workflows:

```bash
cd ~/Work/ContentEngine/scripts/ralph

# Backup current PRD (if needed)
cp prd.json context-capture-prd.json

# Switch to analytics PRD
cp analytics-prd.json prd.json

# Run Ralph
cd ../..
./scripts/ralph/ralph.sh 10
```

## Current PRD Status

To check which PRD is active:

```bash
cat scripts/ralph/prd.json | python -m json.tool | head -5
```

## Avoiding Conflicts

**IMPORTANT:** Only run one Ralph session at a time!

- Check for running Ralph: `ps aux | grep ralph`
- Kill if needed: `pkill -f ralph.sh`

## PRD Best Practices

1. **Complete current PRD before switching** - Avoid leaving stories half-done
2. **Commit work before switching** - Each PRD should work on separate feature branch
3. **Review progress.txt** - Learn from each Ralph session
4. **Archive completed PRDs** - Rename with completion date (e.g., `context-capture-COMPLETE-2026-01-12.json`)

## Quick Start: Analytics Integration

```bash
# 1. Switch to analytics PRD
cd ~/Work/ContentEngine/scripts/ralph
cp analytics-prd.json prd.json

# 2. Verify PRD loaded
cat prd.json | python -m json.tool | grep branchName
# Should show: "branchName": "feature/linkedin-analytics"

# 3. Run Ralph
cd ../..
./scripts/ralph/ralph.sh 10

# 4. Monitor progress
tail -f scripts/ralph/progress.txt
```

## After Ralph Completes

```bash
# Check results
cat scripts/ralph/prd.json | python -m json.tool | grep passes

# Test the analytics
uv run content-engine collect-analytics

# View dashboard
python scripts/analytics_dashboard.py
```

## Troubleshooting

**"Ralph is working on wrong PRD"**
- Check: `cat scripts/ralph/prd.json | grep branchName`
- Fix: Copy correct PRD to `prd.json`

**"Stories keep failing"**
- Review: `tail -20 scripts/ralph/progress.txt`
- Check tests: `uv run pytest -v`
- Adjust acceptance criteria if needed

**"Multiple Ralph processes running"**
- List: `ps aux | grep ralph`
- Kill all: `pkill -f ralph.sh`
- Restart with single PRD
