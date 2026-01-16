# Migration Guide: Custom Scripts → Alembic

If you're currently using the old migration scripts (`scripts/migrate_database_schema.py`), follow this guide to transition to Alembic.

## Quick Migration

```bash
# 1. Backup your database
cp content.db content.db.backup-$(date +%Y%m%d)

# 2. Initialize Alembic (already done - alembic/ directory exists)

# 3. Stamp your database (mark it as current)
uv run alembic stamp head

# 4. Verify
uv run alembic current

# Done! Now use Alembic for all migrations
```

## What Changed?

### Before (Custom Scripts)

```bash
# Make schema changes
# Edit scripts/migrate_database_schema.py
python scripts/migrate_database_schema.py
```

**Problems:**
- No version tracking
- Manual backup/delete/restore cycle
- Risk of data loss
- Hard to collaborate
- Can't rollback changes

### After (Alembic)

```bash
# Make schema changes in lib/database.py
# Generate migration
uv run alembic revision --autogenerate -m "Description"

# Apply migration
uv run alembic upgrade head
```

**Benefits:**
- Full version tracking in git
- Reversible migrations
- Safe upgrades (no delete/recreate)
- Industry standard
- Team-friendly

## Benefits of Alembic

1. **Version Control** - Every schema change is tracked
2. **Reversible** - Can downgrade to previous versions
3. **Portable** - Same migrations work on all environments
4. **Industry Standard** - Used by most Python projects
5. **Safe** - No more "backup → delete → restore" cycles
6. **Collaborative** - Multiple developers can work on schema changes

## Side-by-Side Comparison

| Task | Old Way | New Way (Alembic) |
|------|---------|-------------------|
| **Add column** | Edit `migrate_database_schema.py`, backup DB, run script | Edit `lib/database.py`, run `alembic revision --autogenerate`, run `alembic upgrade head` |
| **Check DB version** | No way to check | `alembic current` |
| **Rollback changes** | Restore from backup | `alembic downgrade -1` |
| **Fresh DB setup** | Run init_db() | `alembic upgrade head` |
| **Track changes** | Manual notes | Git history of `alembic/versions/` |
| **Deploy to server** | Copy DB or run script | Pull code, run `alembic upgrade head` |

## Migration Examples

### Example 1: Add New Column

**Old Way:**
```python
# Edit scripts/migrate_database_schema.py
def migrate():
    backup_posts()
    delete_database()
    recreate_with_new_column()
    restore_posts()
```

**New Way:**
```python
# 1. Edit lib/database.py
class User(Base):
    # ...
    favorite_color = Column(String(50), nullable=True)  # Add this

# 2. Generate migration
uv run alembic revision --autogenerate -m "Add favorite_color to users"

# 3. Apply
uv run alembic upgrade head

# Done! No data loss, fully reversible
```

### Example 2: Rename Column

**Old Way:**
```python
# Risky - might lose data
# Need custom SQL to preserve data
```

**New Way:**
```python
# 1. Generate migration
uv run alembic revision -m "Rename user name to full_name"

# 2. Edit generated file
def upgrade():
    op.alter_column('users', 'name', new_column_name='full_name')

def downgrade():
    op.alter_column('users', 'full_name', new_column_name='name')

# 3. Apply
uv run alembic upgrade head
```

### Example 3: Add Enum Value

**Old Way:**
```python
# Delete database, recreate with new enum
# Lose all data or write complex restore logic
```

**New Way:**
```python
# 1. Edit enum in lib/database.py
class PostStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"  # New value

# 2. Generate migration (may need manual editing for SQLite)
uv run alembic revision --autogenerate -m "Add archived status"

# 3. Apply
uv run alembic upgrade head
```

## Old Scripts (Deprecated)

These scripts still exist but are deprecated:

| Script | Status | Alternative |
|--------|--------|-------------|
| `scripts/migrate_database_schema.py` | ⚠️ Deprecated | Use Alembic migrations |
| `scripts/migrate_existing_posts_to_demo.py` | ⚠️ Legacy | Create Alembic data migration |
| `scripts/migrate_oauth.py` | ⚠️ Legacy | Create Alembic data migration |
| `lib/database.py::init_db()` | ⚠️ Deprecated | Use `alembic upgrade head` |

**Do NOT delete these yet** - they're kept for reference and emergency rollback.

## Common Questions

### Q: Can I still use init_db()?

Yes, but it will show a deprecation warning. It's kept for backwards compatibility. New projects should use `alembic upgrade head`.

### Q: What if I need to rollback?

```bash
# Rollback one version
uv run alembic downgrade -1

# Rollback to specific version
uv run alembic downgrade abc123
```

### Q: How do I see what changed?

```bash
# View migration history
uv run alembic history

# View specific migration file
cat alembic/versions/xxx_description.py
```

### Q: What if autogenerate misses something?

Edit the generated migration file before applying:
```bash
uv run alembic revision --autogenerate -m "Add index"
# Edit alembic/versions/xxx_add_index.py
uv run alembic upgrade head
```

### Q: Can I create custom migrations?

Yes:
```bash
# Create empty migration
uv run alembic revision -m "Custom data migration"

# Edit the file with custom logic
# Apply
uv run alembic upgrade head
```

### Q: How do I test migrations?

```bash
# Backup first
cp content.db content.db.test

# Test upgrade
uv run alembic upgrade head

# Test downgrade
uv run alembic downgrade -1

# Test re-upgrade
uv run alembic upgrade head

# Restore if needed
rm content.db
cp content.db.test content.db
```

## Transition Checklist

- [ ] Backup current database
- [ ] Verify Alembic is initialized (alembic/ directory exists)
- [ ] Stamp database as current: `uv run alembic stamp head`
- [ ] Verify version: `uv run alembic current`
- [ ] Read DATABASE.md for Alembic commands
- [ ] Update local docs/scripts that reference old migration scripts
- [ ] Create first Alembic migration for next schema change
- [ ] Stop using old migration scripts

## Help

See [DATABASE.md](DATABASE.md) for complete Alembic guide.

For issues, check [Troubleshooting section in DATABASE.md](DATABASE.md#troubleshooting).
