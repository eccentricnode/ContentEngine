"""Context synthesizer module for generating structured insights using LLM."""

import json
import os
import requests
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from lib.context_capture import ProjectNote, SessionSummary
from lib.errors import AIError
from lib.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DailyContext:
    """
    Structured representation of synthesized daily context.

    Attributes:
        themes: Key themes from the day's work
        decisions: Important decisions made
        progress: Progress made on projects
        date: Date of the context (YYYY-MM-DD format)
        raw_data: Optional dict containing raw session/project data
    """

    themes: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    progress: List[str] = field(default_factory=list)
    date: str = ""
    raw_data: dict = field(default_factory=dict)


def check_ollama_health(host: Optional[str] = None) -> bool:
    """
    Check if Ollama service is running and accessible.

    Args:
        host: Ollama server URL (defaults to env var OLLAMA_HOST or localhost)

    Returns:
        True if Ollama is accessible, False otherwise
    """
    ollama_host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def synthesize_daily_context(
    sessions: List[SessionSummary],
    projects: List[ProjectNote],
    date: str,
    host: Optional[str] = None,
    model: str = "llama3:8b",
) -> DailyContext:
    """
    Synthesize daily context from session history and project notes using Ollama.

    Args:
        sessions: List of SessionSummary objects from the day
        projects: List of ProjectNote objects
        date: Date string (YYYY-MM-DD)
        host: Ollama server URL (defaults to env var or localhost)
        model: LLM model to use (defaults to llama3:8b)

    Returns:
        DailyContext object with structured insights

    Raises:
        AIError: If Ollama connection fails or response is invalid
    """
    ollama_host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # Check health first
    if not check_ollama_health(ollama_host):
        raise AIError(
            f"Ollama service not accessible at {ollama_host}. "
            "Make sure Ollama is running."
        )

    # Build context summary from sessions and projects
    context_summary = _build_context_summary(sessions, projects)

    # Construct prompt for LLM
    prompt = f"""Analyze the following work context from {date} and extract key insights.

{context_summary}

Summarize key themes, decisions, and progress from today. Focus on:
- Projects worked on
- Decisions made
- Insights gained
- Progress achieved

Output ONLY valid JSON with these exact keys: themes, decisions, progress
Each value should be a list of strings (3-5 items per category).

Example format:
{{"themes": ["theme1", "theme2"], "decisions": ["decision1"], "progress": ["progress1"]}}"""

    try:
        logger.info(f"Sending context to Ollama ({model}) for synthesis...")

        response = requests.post(
            f"{ollama_host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120,
        )
        response.raise_for_status()

        result = response.json()
        llm_response = result.get("response", "").strip()

        logger.debug(f"Ollama response: {llm_response}")

        # Parse JSON response
        try:
            parsed_data = json.loads(llm_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}")
            logger.error(f"Raw response: {llm_response}")
            raise AIError(f"Ollama returned invalid JSON: {e}")

        # Extract structured data
        themes = parsed_data.get("themes", [])
        decisions = parsed_data.get("decisions", [])
        progress = parsed_data.get("progress", [])

        # Ensure they're lists
        if not isinstance(themes, list):
            themes = [str(themes)] if themes else []
        if not isinstance(decisions, list):
            decisions = [str(decisions)] if decisions else []
        if not isinstance(progress, list):
            progress = [str(progress)] if progress else []

        logger.info(
            f"Synthesis complete: {len(themes)} themes, "
            f"{len(decisions)} decisions, {len(progress)} progress items"
        )

        return DailyContext(
            themes=themes,
            decisions=decisions,
            progress=progress,
            date=date,
            raw_data={
                "sessions_count": len(sessions),
                "projects_count": len(projects),
            },
        )

    except requests.exceptions.ConnectionError:
        raise AIError(
            f"Could not connect to Ollama at {ollama_host}. "
            "Make sure Ollama is running."
        )
    except requests.exceptions.Timeout:
        raise AIError("Ollama request timed out. Try again or use a smaller context.")
    except requests.exceptions.RequestException as e:
        raise AIError(f"Ollama request failed: {e}")
    except Exception as e:
        raise AIError(f"Ollama request failed: {e}")


def _build_context_summary(
    sessions: List[SessionSummary], projects: List[ProjectNote]
) -> str:
    """
    Build a text summary of sessions and projects for LLM input.

    Args:
        sessions: List of SessionSummary objects
        projects: List of ProjectNote objects

    Returns:
        Formatted context summary string
    """
    lines = []

    # Sessions summary
    if sessions:
        lines.append("## Sessions")
        for i, session in enumerate(sessions[:10], 1):  # Limit to 10 sessions
            lines.append(f"\n### Session {i}")
            if session.topics:
                lines.append(f"Topics: {', '.join(session.topics[:5])}")
            if session.decisions:
                lines.append(f"Decisions: {', '.join(session.decisions[:3])}")

    # Projects summary
    if projects:
        lines.append("\n## Projects")
        for project in projects[:10]:  # Limit to 10 projects
            lines.append(f"\n### {project.project_name}")
            if project.current_status:
                lines.append(f"Status: {project.current_status}")
            if project.key_insights:
                lines.append(f"Insights: {', '.join(project.key_insights[:3])}")

    return "\n".join(lines)


def save_context(context: DailyContext, output_dir: str = "context") -> str:
    """
    Save DailyContext to a JSON file.

    Args:
        context: DailyContext object to save
        output_dir: Directory to save context files (defaults to "context/")

    Returns:
        Path to the saved file

    Raises:
        OSError: If file write fails
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Use date from context or today
    filename = f"{context.date or 'unknown'}.json"
    file_path = output_path / filename

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(context), f, indent=2, default=str)

        logger.info(f"Context saved to {file_path}")
        return str(file_path)

    except Exception as e:
        logger.error(f"Failed to save context: {e}")
        raise OSError(f"Failed to save context to {file_path}: {e}")
