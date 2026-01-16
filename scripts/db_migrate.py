#!/usr/bin/env python3
"""Database migration helper commands."""
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_cmd(cmd: list[str]) -> int:
    """Run command in project root."""
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/db_migrate.py [command]")
        print("\nCommands:")
        print("  init       - Initialize database to latest schema")
        print("  upgrade    - Upgrade database to latest version")
        print("  downgrade  - Downgrade database by one version")
        print("  current    - Show current migration version")
        print("  history    - Show migration history")
        print("  create     - Create new migration (autogenerate)")
        print("  reset      - Reset database (DESTRUCTIVE)")
        return 1

    command = sys.argv[1]

    if command == "init":
        print("🔧 Initializing database...")
        return run_cmd(["uv", "run", "alembic", "upgrade", "head"])

    elif command == "upgrade":
        print("⬆️  Upgrading database...")
        return run_cmd(["uv", "run", "alembic", "upgrade", "head"])

    elif command == "downgrade":
        print("⬇️  Downgrading database...")
        return run_cmd(["uv", "run", "alembic", "downgrade", "-1"])

    elif command == "current":
        return run_cmd(["uv", "run", "alembic", "current"])

    elif command == "history":
        return run_cmd(["uv", "run", "alembic", "history", "--verbose"])

    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Provide migration message")
            print('Example: python scripts/db_migrate.py create "Add user preferences table"')
            return 1
        message = sys.argv[2]
        print(f"📝 Creating migration: {message}")
        return run_cmd(["uv", "run", "alembic", "revision", "--autogenerate", "-m", message])

    elif command == "reset":
        print("⚠️  WARNING: This will DELETE ALL DATA!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm != "yes":
            print("Aborted.")
            return 1

        db_path = PROJECT_ROOT / "content.db"
        if db_path.exists():
            db_path.unlink()
            print(f"🗑️  Deleted {db_path}")

        print("🔧 Recreating database with latest schema...")
        return run_cmd(["uv", "run", "alembic", "upgrade", "head"])

    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
