"""Context capture module for reading PAI session history and project notes."""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SessionSummary:
    """
    Structured representation of a PAI session.

    Attributes:
        session_id: Unique identifier for the session
        date: Session date
        duration_minutes: Session duration in minutes (if available)
        topics: List of topics discussed
        decisions: Key decisions made during session
        file_path: Path to the original session file
    """

    session_id: str
    date: datetime
    duration_minutes: Optional[int] = None
    topics: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    file_path: str = ""


@dataclass
class ProjectNote:
    """
    Structured representation of a project note from Folio.

    Attributes:
        project_name: Name of the project
        last_updated: Last modification date
        key_insights: List of key insights or notes
        current_status: Current status of the project
        file_path: Path to the original markdown file
        tags: Optional tags from frontmatter
    """

    project_name: str
    last_updated: datetime
    key_insights: List[str] = field(default_factory=list)
    current_status: str = ""
    file_path: str = ""
    tags: List[str] = field(default_factory=list)


def read_session_history(
    session_dir: Optional[str] = None, limit: Optional[int] = None
) -> List[SessionSummary]:
    """
    Read and parse PAI session history from JSON files.

    Args:
        session_dir: Path to session directory (defaults to ~/.claude/History/Sessions/)
        limit: Maximum number of sessions to return (most recent first)

    Returns:
        List of SessionSummary objects, sorted by date (most recent first)

    Raises:
        FileNotFoundError: If session directory does not exist
    """
    if session_dir is None:
        session_dir = os.path.expanduser("~/.claude/History/Sessions/")

    session_path = Path(session_dir)

    if not session_path.exists():
        logger.warning(f"Session directory not found: {session_path}")
        raise FileNotFoundError(f"Session directory not found: {session_path}")

    summaries: List[SessionSummary] = []

    # Find all JSON and JSONL files
    json_files = list(session_path.glob("*.json")) + list(session_path.glob("*.jsonl"))

    if not json_files:
        logger.info(f"No session files found in {session_path}")
        return summaries

    logger.info(f"Found {len(json_files)} session files")

    for file_path in json_files:
        try:
            summary = _parse_session_file(file_path)
            if summary:
                summaries.append(summary)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            continue

    # Sort by date, most recent first
    summaries.sort(key=lambda s: s.date, reverse=True)

    if limit:
        summaries = summaries[:limit]

    logger.info(f"Successfully parsed {len(summaries)} sessions")
    return summaries


def _parse_session_file(file_path: Path) -> Optional[SessionSummary]:
    """
    Parse a single session file (JSON or JSONL format).

    Args:
        file_path: Path to session file

    Returns:
        SessionSummary object or None if parsing fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try parsing as standard JSON first
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try parsing as JSONL (multiple JSON objects per line)
            lines = content.strip().split("\n")
            if len(lines) > 0:
                # Take the first valid JSON line
                for line in lines:
                    try:
                        data = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
                else:
                    logger.warning(f"No valid JSON found in JSONL file: {file_path}")
                    return None
            else:
                return None

        # Extract session metadata
        session_id = data.get("sessionId", file_path.stem)

        # Parse date from various possible fields
        date_str = data.get("startTime") or data.get("created_at") or data.get("timestamp")
        if date_str:
            try:
                # Handle ISO format timestamps
                if isinstance(date_str, str):
                    if "T" in date_str:
                        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                else:
                    # Unix timestamp
                    date = datetime.fromtimestamp(date_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                # Fallback to file modification time
                date = datetime.fromtimestamp(file_path.stat().st_mtime)
        else:
            # Use file modification time as fallback
            date = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Extract duration if available
        duration_minutes = None
        if "duration" in data:
            try:
                duration_minutes = int(data["duration"])
            except (ValueError, TypeError):
                pass

        # Extract topics from messages or summary
        topics = _extract_topics(data)

        # Extract decisions from messages
        decisions = _extract_decisions(data)

        return SessionSummary(
            session_id=session_id,
            date=date,
            duration_minutes=duration_minutes,
            topics=topics,
            decisions=decisions,
            file_path=str(file_path),
        )

    except Exception as e:
        logger.error(f"Error parsing session file {file_path}: {e}")
        return None


def _extract_topics(data: Dict[str, Any]) -> List[str]:
    """
    Extract discussion topics from session data.

    Args:
        data: Session JSON data

    Returns:
        List of topic strings
    """
    topics = []

    # Check for explicit topics field
    if "topics" in data and isinstance(data["topics"], list):
        topics.extend(data["topics"])

    # Check for summary field
    if "summary" in data and isinstance(data["summary"], str):
        topics.append(data["summary"])

    # Extract from messages if present
    if "messages" in data and isinstance(data["messages"], list):
        for msg in data["messages"][:5]:  # Check first 5 messages
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > 20:
                    # Extract first line/sentence as topic indicator
                    first_line = content.split("\n")[0][:100]
                    if first_line and first_line not in topics:
                        topics.append(first_line)

    return topics[:10]  # Limit to 10 topics


def _extract_decisions(data: Dict[str, Any]) -> List[str]:
    """
    Extract key decisions from session data.

    Args:
        data: Session JSON data

    Returns:
        List of decision strings
    """
    decisions = []

    # Check for explicit decisions field
    if "decisions" in data and isinstance(data["decisions"], list):
        decisions.extend(data["decisions"])

    # Look for decision keywords in messages
    if "messages" in data and isinstance(data["messages"], list):
        decision_keywords = ["decided", "decision", "will implement", "going with", "chose"]
        for msg in data["messages"]:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str):
                    content_lower = content.lower()
                    for keyword in decision_keywords:
                        if keyword in content_lower:
                            # Extract the sentence containing the keyword
                            sentences = content.split(".")
                            for sentence in sentences:
                                if keyword in sentence.lower():
                                    clean_sentence = sentence.strip()[:200]
                                    if clean_sentence and clean_sentence not in decisions:
                                        decisions.append(clean_sentence)
                                    break

    return decisions[:5]  # Limit to 5 key decisions


def read_project_notes(
    projects_dir: Optional[str] = None, limit: Optional[int] = None
) -> List[ProjectNote]:
    """
    Read and parse project notes from Folio markdown files.

    Args:
        projects_dir: Path to projects directory (defaults to ~/Documents/Folio/1-Projects/)
        limit: Maximum number of project notes to return (most recent first)

    Returns:
        List of ProjectNote objects, sorted by last_updated (most recent first)

    Raises:
        FileNotFoundError: If projects directory does not exist
    """
    if projects_dir is None:
        projects_dir = os.path.expanduser("~/Documents/Folio/1-Projects/")

    projects_path = Path(projects_dir)

    if not projects_path.exists():
        logger.warning(f"Projects directory not found: {projects_path}")
        raise FileNotFoundError(f"Projects directory not found: {projects_path}")

    notes: List[ProjectNote] = []

    # Find all markdown files (use rglob to avoid duplicates)
    md_files = list(projects_path.rglob("*.md"))

    if not md_files:
        logger.info(f"No markdown files found in {projects_path}")
        return notes

    logger.info(f"Found {len(md_files)} markdown files")

    for file_path in md_files:
        try:
            note = _parse_project_note(file_path)
            if note:
                notes.append(note)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            continue

    # Sort by last_updated, most recent first
    notes.sort(key=lambda n: n.last_updated, reverse=True)

    if limit:
        notes = notes[:limit]

    logger.info(f"Successfully parsed {len(notes)} project notes")
    return notes


def _parse_project_note(file_path: Path) -> Optional[ProjectNote]:
    """
    Parse a single markdown project note file.

    Args:
        file_path: Path to markdown file

    Returns:
        ProjectNote object or None if parsing fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract project name from filename or frontmatter
        project_name = file_path.stem.replace("-", " ").replace("_", " ").title()

        # Get last updated from file modification time
        last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Try parsing frontmatter first
        frontmatter_data = _parse_frontmatter(content)

        if frontmatter_data:
            # Override with frontmatter values if present
            project_name = frontmatter_data.get("title", project_name)
            if "date" in frontmatter_data or "updated" in frontmatter_data:
                date_str = frontmatter_data.get("updated") or frontmatter_data.get("date")
                try:
                    if isinstance(date_str, str):
                        last_updated = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            tags = frontmatter_data.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            elif not isinstance(tags, list):
                tags = []

            # Extract status from frontmatter
            current_status = frontmatter_data.get("status", "")
        else:
            tags = []
            current_status = ""

        # Parse markdown content for insights and status
        key_insights, parsed_status = _parse_markdown_content(content)

        # Use parsed status if no frontmatter status
        if not current_status:
            current_status = parsed_status

        return ProjectNote(
            project_name=project_name,
            last_updated=last_updated,
            key_insights=key_insights,
            current_status=current_status,
            file_path=str(file_path),
            tags=tags,
        )

    except Exception as e:
        logger.error(f"Error parsing project note {file_path}: {e}")
        return None


def _parse_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Dictionary of frontmatter data or None if no frontmatter
    """
    # Check for YAML frontmatter (--- at start and end)
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_text = parts[1].strip()

    # Simple YAML parser for common patterns (key: value)
    frontmatter_data: Dict[str, Any] = {}

    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Match "key: value" pattern
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.+)$", line)
        if match:
            key, value = match.groups()
            value = value.strip()

            # Handle quoted strings
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            # Handle arrays [item1, item2]
            if value.startswith("[") and value.endswith("]"):
                items = value[1:-1].split(",")
                value = [item.strip().strip('"').strip("'") for item in items if item.strip()]

            frontmatter_data[key] = value

    return frontmatter_data if frontmatter_data else None


def _parse_markdown_content(content: str) -> tuple[List[str], str]:
    """
    Parse markdown content to extract key insights and status.

    Args:
        content: Markdown file content

    Returns:
        Tuple of (key_insights list, current_status string)
    """
    # Remove frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    key_insights: List[str] = []
    current_status = ""

    lines = content.split("\n")

    # Track current section
    current_section = ""

    for line in lines:
        line = line.strip()

        # Check for headings
        if line.startswith("#"):
            heading_match = re.match(r"^#+\s+(.+)$", line)
            if heading_match:
                current_section = heading_match.group(1).lower()

        # Extract status from status sections
        if current_section in ["status", "current status", "project status"]:
            if line and not line.startswith("#"):
                if not current_status:
                    current_status = line[:200]

        # Extract insights from key sections
        if current_section in [
            "insights",
            "key insights",
            "learnings",
            "notes",
            "summary",
            "overview",
        ]:
            # Extract bullet points or sentences
            if line.startswith("-") or line.startswith("*"):
                insight = line.lstrip("-*").strip()
                if insight and len(insight) > 10:
                    key_insights.append(insight[:300])
            elif line and not line.startswith("#") and len(line) > 20:
                key_insights.append(line[:300])

    # Limit insights
    key_insights = key_insights[:10]

    return key_insights, current_status
