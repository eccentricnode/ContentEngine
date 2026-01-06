"""LinkedIn posting agent for Content Engine."""

import sys
import argparse
import requests
from typing import Dict, Any

from lib.config import get_linkedin_config
from lib.errors import LinkedInAPIError, ConfigurationError
from lib.logger import setup_logger


logger = setup_logger(__name__)


def create_post_payload(content: str, user_sub: str) -> Dict[str, Any]:
    """
    Create LinkedIn API post payload.

    Args:
        content: Post content text (max 3000 chars)
        user_sub: LinkedIn user sub identifier

    Returns:
        API request payload dict
    """
    return {
        "author": f"urn:li:person:{user_sub}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content,
                },
                "shareMediaCategory": "NONE",
            },
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }


def post_to_linkedin(content: str, access_token: str, user_sub: str, dry_run: bool = False) -> str:
    """
    Post content to LinkedIn.

    Args:
        content: Post content text
        access_token: LinkedIn OAuth access token
        user_sub: LinkedIn user sub identifier
        dry_run: If True, don't actually post (just validate)

    Returns:
        Post ID if successful

    Raises:
        LinkedInAPIError: If API request fails
    """
    if len(content) > 3000:
        raise ValueError(f"Content too long: {len(content)} chars (max 3000)")

    payload = create_post_payload(content, user_sub)

    logger.info("=" * 60)
    logger.info("LinkedIn Post")
    logger.info("=" * 60)
    logger.info(f"Content: {content}")
    logger.info(f"Length: {len(content)} / 3000 chars")
    logger.info(f"Visibility: PUBLIC")
    logger.info(f"Author URN: urn:li:person:{user_sub}")

    if dry_run:
        logger.info("\n🧪 DRY RUN - Not actually posting")
        logger.info(f"Payload: {payload}")
        return "dry-run-post-id"

    logger.info("\n🚀 Posting to LinkedIn...")

    try:
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
            timeout=30,
        )

        if not response.ok:
            error_body = response.text
            logger.error(f"❌ Post failed: {response.status_code} {response.reason}")
            logger.error(f"Response: {error_body}")

            if response.status_code == 401:
                logger.error("\n💡 Token may be expired. Run oauth flow again.")

            raise LinkedInAPIError(
                status_code=response.status_code,
                message=response.reason,
                response_body=error_body,
            )

        post_id = response.headers.get("X-RestLi-Id", "unknown")
        logger.info(f"✅ Posted successfully!")
        logger.info(f"Post ID: {post_id}")
        logger.info("\nView at: https://www.linkedin.com/feed/")

        return post_id

    except requests.RequestException as e:
        raise LinkedInAPIError(
            status_code=0,
            message=f"Request failed: {str(e)}",
        )


def main() -> None:
    """CLI entry point for LinkedIn posting."""
    parser = argparse.ArgumentParser(description="Post content to LinkedIn")
    parser.add_argument("content", help="Post content text")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test without actually posting"
    )
    args = parser.parse_args()

    try:
        config = get_linkedin_config()

        if not config.access_token or not config.user_sub:
            raise ConfigurationError(
                "Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_USER_SUB. "
                "Run OAuth flow first."
            )

        post_to_linkedin(
            content=args.content,
            access_token=config.access_token,
            user_sub=config.user_sub,
            dry_run=args.dry_run,
        )

    except (LinkedInAPIError, ConfigurationError, ValueError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
