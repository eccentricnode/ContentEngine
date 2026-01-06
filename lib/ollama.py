"""Ollama integration for AI-powered content generation."""

import os
import requests
from typing import Optional, Dict, Any
from lib.errors import AIError


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, host: Optional[str] = None, model: str = "llama3.2"):
        """Initialize Ollama client.

        Args:
            host: Ollama server URL (defaults to env var OLLAMA_HOST or localhost)
            model: Model to use (defaults to llama3.2)
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model
        self.api_url = f"{self.host}/api/generate"

    def generate_content_ideas(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate content ideas using Ollama.

        Args:
            prompt: User's request for content ideas
            context: Optional context about previous conversation

        Returns:
            Generated content suggestion

        Raises:
            AIError: If Ollama request fails
        """
        system_prompt = """You are a LinkedIn content strategist helping Austin Johnson create engaging posts.

Austin is:
- Software Engineer & AI Engineer
- Building AI-first systems
- Currently interviewing for Principal Engineer roles
- Passionate about AI as a force multiplier for engineers

Generate content ideas that:
- Are authentic and insightful
- Focus on AI engineering, development, or career growth
- Are 1-3 paragraphs (LinkedIn-appropriate length)
- Include specific examples or takeaways
- Avoid buzzwords and hype

When suggesting content, provide the actual post text ready to publish."""

        full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
        if context:
            full_prompt += f"\n\nPrevious context: {context}"

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            raise AIError(
                f"Could not connect to Ollama at {self.host}. "
                "Make sure Ollama is running."
            )
        except requests.exceptions.Timeout:
            raise AIError("Ollama request timed out. Try again.")
        except requests.exceptions.RequestException as e:
            raise AIError(f"Ollama request failed: {e}")

    def chat(self, message: str, conversation_history: list[Dict[str, str]]) -> str:
        """Have a conversation with Ollama.

        Args:
            message: Current user message
            conversation_history: List of previous messages [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            AI response
        """
        # Build conversation context
        context = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in conversation_history[-5:]  # Last 5 messages for context
        ])

        return self.generate_content_ideas(message, context)


def get_ollama_client() -> OllamaClient:
    """Get configured Ollama client."""
    return OllamaClient()
