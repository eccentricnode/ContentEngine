"""LinkedIn OAuth 2.0 server for Content Engine."""

import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import requests

from lib.config import get_linkedin_config, get_server_config
from lib.errors import OAuthError
from lib.logger import setup_logger


logger = setup_logger(__name__)


class OAuthHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    auth_code: str | None = None

    def log_message(self, format: str, *args) -> None:
        """Override to use custom logger."""
        logger.info(format % args)

    def do_GET(self) -> None:
        """Handle OAuth callback GET request."""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/":
            # Initial page - redirect to LinkedIn
            config = get_linkedin_config()
            auth_url = (
                "https://www.linkedin.com/oauth/v2/authorization"
                f"?response_type=code"
                f"&client_id={config.client_id}"
                f"&redirect_uri={config.redirect_uri}"
                f"&scope=openid%20profile%20w_member_social"
            )

            self.send_response(302)
            self.send_header("Location", auth_url)
            self.end_headers()

        elif parsed_url.path == "/auth/callback":
            # OAuth callback with authorization code
            query_params = parse_qs(parsed_url.query)

            if "error" in query_params:
                error = query_params["error"][0]
                logger.error(f"OAuth error: {error}")
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h1>Error: {error}</h1>".encode())
                return

            if "code" not in query_params:
                logger.error("No authorization code in callback")
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Error: No authorization code</h1>")
                return

            OAuthHandler.auth_code = query_params["code"][0]
            logger.info(f"✅ Received authorization code: {OAuthHandler.auth_code[:20]}...")

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Success!</h1>"
                b"<p>Authorization code received. You can close this window.</p>"
                b"<p>Check your terminal for next steps.</p>"
            )

        else:
            self.send_response(404)
            self.end_headers()


def update_env_file(access_token: str, user_sub: str) -> None:
    """
    Update .env file with new access token and user sub.

    Args:
        access_token: LinkedIn access token
        user_sub: LinkedIn user sub identifier
    """
    env_path = Path(".env")

    if not env_path.exists():
        logger.warning(".env file not found, creating new one")
        env_path.touch()

    # Read existing .env
    lines = env_path.read_text().splitlines()

    # Update or add tokens
    updated_lines = []
    token_found = False
    sub_found = False

    for line in lines:
        if line.startswith("LINKEDIN_ACCESS_TOKEN="):
            updated_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}")
            token_found = True
        elif line.startswith("LINKEDIN_USER_SUB="):
            updated_lines.append(f"LINKEDIN_USER_SUB={user_sub}")
            sub_found = True
        else:
            updated_lines.append(line)

    # Add if not found
    if not token_found:
        updated_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    if not sub_found:
        updated_lines.append(f"LINKEDIN_USER_SUB={user_sub}")

    # Write back
    env_path.write_text("\n".join(updated_lines) + "\n")
    logger.info("✅ Updated .env file with new credentials")


def exchange_code_for_token(auth_code: str) -> tuple[str, str]:
    """
    Exchange authorization code for access token.

    Args:
        auth_code: OAuth authorization code

    Returns:
        Tuple of (access_token, user_sub)

    Raises:
        OAuthError: If token exchange fails
    """
    config = get_linkedin_config()

    logger.info("Exchanging authorization code for access token...")

    try:
        response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": config.redirect_uri,
            },
            timeout=30,
        )

        if not response.ok:
            raise OAuthError(f"Token exchange failed: {response.status_code} {response.text}")

        token_data = response.json()
        access_token = token_data["access_token"]

        logger.info("✅ Access token received")

        # Get user info (for user_sub)
        user_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

        if not user_response.ok:
            raise OAuthError(f"User info request failed: {user_response.status_code}")

        user_data = user_response.json()
        user_sub = user_data["sub"]

        logger.info(f"✅ User sub received: {user_sub}")

        return access_token, user_sub

    except requests.RequestException as e:
        raise OAuthError(f"Request failed: {str(e)}")


def main() -> None:
    """Run OAuth server."""
    logger.info("=" * 60)
    logger.info("LinkedIn OAuth 2.0 Server")
    logger.info("=" * 60)

    server_config = get_server_config()
    linkedin_config = get_linkedin_config()

    server_address = (server_config.host, server_config.port)
    httpd = HTTPServer(server_address, OAuthHandler)

    logger.info(f"\n🌐 Server running at http://localhost:{server_config.port}")
    logger.info("Opening browser for LinkedIn authorization...")
    logger.info("Waiting for OAuth callback...\n")

    # Open browser
    webbrowser.open(f"http://localhost:{server_config.port}")

    # Handle requests until we get the auth code
    while OAuthHandler.auth_code is None:
        httpd.handle_request()

    httpd.server_close()

    # Exchange code for token
    try:
        access_token, user_sub = exchange_code_for_token(OAuthHandler.auth_code)

        logger.info("\n" + "=" * 60)
        logger.info("🎉 OAuth flow completed successfully!")
        logger.info("=" * 60)

        # Auto-save to .env
        try:
            update_env_file(access_token, user_sub)
            logger.info("\n✅ Credentials saved to .env file automatically!")
            logger.info("\nYou can now use:")
            logger.info("  uv run python -m agents.linkedin.test_connection")
            logger.info("  uv run content-engine draft 'Your post'\n")
        except Exception as e:
            logger.warning(f"⚠️  Failed to auto-save to .env: {e}")
            logger.info("\nManually add these to your .env file:")
            logger.info(f"\nLINKEDIN_ACCESS_TOKEN={access_token}")
            logger.info(f"LINKEDIN_USER_SUB={user_sub}\n")

    except OAuthError as e:
        logger.error(f"❌ OAuth error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
