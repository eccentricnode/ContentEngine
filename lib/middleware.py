"""Middleware for Content Engine."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from lib.auth import get_user_from_request


class UserContextMiddleware(BaseHTTPMiddleware):
    """Middleware to inject user context into every request."""

    async def dispatch(self, request: Request, call_next):
        """Process request and inject user context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Get user from session cookie (None if not authenticated)
        user = get_user_from_request(request)

        # Inject user context into request state
        request.state.user = user
        request.state.is_authenticated = user is not None
        request.state.user_mode = 'authenticated' if user else 'demo'

        # Process request
        response = await call_next(request)

        return response
