"""Context capture module for reading PAI session history."""

import json
import os
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
