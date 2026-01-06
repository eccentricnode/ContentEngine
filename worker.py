"""Background worker for scheduled post publishing."""

from datetime import datetime
from sqlalchemy import select

from lib.database import init_db, get_db, Post, PostStatus, Platform, OAuthToken
from lib.logger import setup_logger
from agents.linkedin.post import post_to_linkedin


logger = setup_logger(__name__)


def process_scheduled_posts() -> None:
    """Process all scheduled posts that are due."""
    init_db()
    db = get_db()

    # Find posts scheduled for now or earlier
    query = (
        select(Post)
        .where(Post.status == PostStatus.SCHEDULED)
        .where(Post.scheduled_at <= datetime.utcnow())
        .order_by(Post.scheduled_at)
    )

    posts = db.execute(query).scalars().all()

    if not posts:
        logger.info("No scheduled posts to process")
        db.close()
        return

    logger.info(f"Found {len(posts)} scheduled post(s) to process")

    for post in posts:
        logger.info(f"Processing post {post.id} (scheduled for {post.scheduled_at})")

        # Get OAuth token for platform
        token_query = select(OAuthToken).where(OAuthToken.platform == post.platform)
        oauth_token = db.execute(token_query).scalar_one_or_none()

        if not oauth_token:
            logger.error(f"No OAuth token found for {post.platform.value}")
            post.status = PostStatus.FAILED
            post.error_message = f"No OAuth token for {post.platform.value}"
            db.commit()
            continue

        try:
            if post.platform == Platform.LINKEDIN:
                external_id = post_to_linkedin(
                    content=post.content,
                    access_token=oauth_token.access_token,
                    user_sub=oauth_token.user_sub or "",
                    dry_run=False,
                )

                post.status = PostStatus.POSTED
                post.posted_at = datetime.utcnow()
                post.external_id = external_id

                logger.info(f"✅ Post {post.id} published successfully (ID: {external_id})")

            else:
                logger.error(f"Platform {post.platform.value} not yet supported")
                post.status = PostStatus.FAILED
                post.error_message = f"Platform {post.platform.value} not supported"

            db.commit()

        except Exception as e:
            logger.error(f"Failed to post {post.id}: {e}")
            post.status = PostStatus.FAILED
            post.error_message = str(e)
            db.commit()

    db.close()
    logger.info("Worker run complete")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Content Engine Worker Starting")
    logger.info("=" * 60)
    process_scheduled_posts()
