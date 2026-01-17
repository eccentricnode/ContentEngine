#!/usr/bin/env python3
"""
Quick OAuth flow to get LinkedIn Analytics access token.

Run this to authorize the analytics app and get the access token.
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests


# Load from .env
CLIENT_ID = os.getenv("LINKEDIN_ANALYTICS_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_ANALYTICS_CLIENT_SECRET")
# Analytics app has its own redirect URI (separate from posting app)
REDIRECT_URI = "http://localhost:8888/callback"

# Analytics scopes - start with minimum, only request scopes the app has enabled
# Check LinkedIn app → Products tab to see what's available
SCOPES = "openid profile"


class OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/callback":
            params = parse_qs(parsed.query)

            if "error" in params:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error = params["error"][0]
                self.wfile.write(f"<h1>OAuth Error</h1><p>{error}</p>".encode())
                OAuthHandler.auth_code = None
                return

            if "code" in params:
                OAuthHandler.auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h1>Success!</h1><p>Authorization code received. You can close this window.</p>"
                )
                return

        self.send_response(404)
        self.end_headers()


def main():
    print("=" * 60)
    print("LinkedIn Analytics OAuth Flow")
    print("=" * 60)
    print()

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Error: Analytics credentials not found in .env")
        print()
        print("Make sure these are set:")
        print("  LINKEDIN_ANALYTICS_CLIENT_ID")
        print("  LINKEDIN_ANALYTICS_CLIENT_SECRET")
        print()
        print("See LINKEDIN_ANALYTICS_SETUP.md for instructions")
        sys.exit(1)

    # Step 1: Start local server
    print("🚀 Starting OAuth server on http://localhost:8888")
    server = HTTPServer(("localhost", 8888), OAuthHandler)

    # Step 2: Build authorization URL
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
    )

    print()
    print("📋 Opening browser for LinkedIn authorization...")
    print()
    print("If browser doesn't open automatically, visit:")
    print(auth_url)
    print()

    # Open browser
    webbrowser.open(auth_url)

    # Step 3: Wait for callback
    print("⏳ Waiting for authorization...")
    while OAuthHandler.auth_code is None:
        server.handle_request()

    auth_code = OAuthHandler.auth_code
    print()
    print(f"✓ Authorization code received: {auth_code[:20]}...")

    # Step 4: Exchange code for access token
    print()
    print("🔄 Exchanging code for access token...")

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        tokens = response.json()

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token", "")
        expires_in = tokens.get("expires_in", 0)

        print()
        print("=" * 60)
        print("✅ SUCCESS! Access token obtained")
        print("=" * 60)
        print()
        print("Add these to your .env file:")
        print()
        print(f'LINKEDIN_ANALYTICS_ACCESS_TOKEN="{access_token}"')
        if refresh_token:
            print(f'LINKEDIN_ANALYTICS_REFRESH_TOKEN="{refresh_token}"')
        print()
        print(f"Token expires in: {expires_in} seconds (~{expires_in // 3600} hours)")
        print()
        print("Now you can run:")
        print("  uv run content-engine collect-analytics")
        print()

    except requests.exceptions.RequestException as e:
        print()
        print(f"❌ Error getting access token: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
