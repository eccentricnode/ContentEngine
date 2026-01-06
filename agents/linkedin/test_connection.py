"""Test LinkedIn API connection."""

import sys
import requests

from lib.config import get_linkedin_config
from lib.errors import ConfigurationError, LinkedInAPIError
from lib.logger import setup_logger


logger = setup_logger(__name__)


def test_connection() -> None:
    """Test LinkedIn API connection with current credentials."""
    try:
        config = get_linkedin_config()

        if not config.access_token:
            raise ConfigurationError(
                "LINKEDIN_ACCESS_TOKEN not found. Run OAuth flow first."
            )

        logger.info("=" * 60)
        logger.info("Testing LinkedIn API Connection")
        logger.info("=" * 60)

        logger.info("\nFetching user profile...")

        response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {config.access_token}"},
            timeout=30,
        )

        if not response.ok:
            if response.status_code == 401:
                raise LinkedInAPIError(
                    status_code=401,
                    message="Token expired or invalid",
                    response_body=response.text,
                )
            raise LinkedInAPIError(
                status_code=response.status_code,
                message=response.reason,
                response_body=response.text,
            )

        user_data = response.json()

        logger.info("\n✅ Connection successful!")
        logger.info(f"\nUser: {user_data.get('name', 'Unknown')}")
        logger.info(f"Email: {user_data.get('email', 'Unknown')}")
        logger.info(f"Sub: {user_data.get('sub', 'Unknown')}")

        if config.user_sub and user_data.get("sub") != config.user_sub:
            logger.warning(
                f"\n⚠️ Warning: User sub mismatch!"
                f"\nExpected: {config.user_sub}"
                f"\nActual: {user_data.get('sub')}"
                f"\nUpdate LINKEDIN_USER_SUB in .env"
            )

    except (LinkedInAPIError, ConfigurationError) as e:
        logger.error(f"\n❌ Error: {e}")
        sys.exit(1)

    except requests.RequestException as e:
        logger.error(f"\n❌ Request failed: {e}")
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    test_connection()


if __name__ == "__main__":
    main()
