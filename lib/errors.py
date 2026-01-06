"""Custom error types for Content Engine."""


class ContentEngineError(Exception):
    """Base exception for Content Engine."""
    pass


class LinkedInAPIError(ContentEngineError):
    """LinkedIn API error."""

    def __init__(self, status_code: int, message: str, response_body: str = ""):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"LinkedIn API Error {status_code}: {message}")


class OAuthError(ContentEngineError):
    """OAuth authentication error."""
    pass


class ConfigurationError(ContentEngineError):
    """Configuration or environment variable error."""
    pass


class AIError(ContentEngineError):
    """AI/LLM operation error."""
    pass
