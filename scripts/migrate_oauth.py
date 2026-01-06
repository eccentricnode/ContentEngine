"""Migrate OAuth tokens from .env to database."""

from sqlalchemy import select

from lib.config import get_linkedin_config
from lib.database import init_db, get_db, OAuthToken, Platform
from lib.logger import setup_logger


logger = setup_logger(__name__)


def migrate_linkedin_token() -> None:
    """Migrate LinkedIn OAuth token from .env to database."""
    init_db()

    try:
        config = get_linkedin_config()

        if not config.access_token or not config.user_sub:
            logger.error("LINKEDIN_ACCESS_TOKEN or LINKEDIN_USER_SUB not found in .env")
            logger.info("Run OAuth flow first: uv run linkedin-oauth")
            return

        db = get_db()

        # Check if token already exists
        query = select(OAuthToken).where(OAuthToken.platform == Platform.LINKEDIN)
        existing_token = db.execute(query).scalar_one_or_none()

        if existing_token:
            logger.info("Updating existing LinkedIn OAuth token")
            existing_token.access_token = config.access_token
            existing_token.user_sub = config.user_sub
        else:
            logger.info("Creating new LinkedIn OAuth token")
            token = OAuthToken(
                platform=Platform.LINKEDIN,
                access_token=config.access_token,
                user_sub=config.user_sub,
            )
            db.add(token)

        db.commit()
        logger.info("✅ LinkedIn OAuth token migrated to database successfully")
        logger.info(f"User SUB: {config.user_sub}")

        db.close()

    except Exception as e:
        logger.error(f"Failed to migrate OAuth token: {e}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("OAuth Token Migration")
    logger.info("=" * 60)
    migrate_linkedin_token()
