"""Job Worker for ContentEngine.

Processes the SQLite job queue and executes scheduled posts.

Usage:
    uv run python job_worker.py              # Process all due jobs once
    uv run python job_worker.py --continuous # Run continuously (daemon mode)
    uv run python job_worker.py --dry-run    # Preview without posting
"""

import argparse
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

from lib.database import (
    get_db,
    Post,
    PostStatus,
    Platform,
    JobQueue,
    JobStatus,
    JobType,
    OAuthToken,
)
from lib.logger import setup_logger
from agents.linkedin.post import post_to_linkedin

logger = setup_logger(__name__)


class JobWorker:
    """Worker that processes the job queue."""

    # Retry backoff schedule (in seconds)
    RETRY_BACKOFF = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr

    def __init__(self, dry_run: bool = False) -> None:
        """Initialize worker.

        Args:
            dry_run: If True, don't actually post, just simulate
        """
        self.dry_run = dry_run

    def process_queue(self) -> int:
        """Process all due jobs in the queue.

        Returns:
            Number of jobs processed
        """
        db = get_db()
        now = datetime.utcnow()

        # Get jobs that are due
        # Due = scheduled_at is NULL (immediate) or scheduled_at <= now
        # And next_retry_at is NULL or <= now
        jobs = db.query(JobQueue).filter(
            JobQueue.status == JobStatus.PENDING,
            (JobQueue.scheduled_at.is_(None) | (JobQueue.scheduled_at <= now)),
            (JobQueue.next_retry_at.is_(None) | (JobQueue.next_retry_at <= now))
        ).order_by(
            JobQueue.priority.desc(),
            JobQueue.scheduled_at.asc()
        ).all()

        if not jobs:
            logger.info("No jobs to process")
            return 0

        logger.info(f"Found {len(jobs)} jobs to process")

        processed = 0
        for job in jobs:
            try:
                self._process_job(db, job)
                processed += 1
            except Exception as e:
                logger.exception(f"Failed to process job {job.id}")
                self._handle_failure(db, job, str(e))

        db.close()
        return processed

    def _process_job(self, db, job: JobQueue) -> None:
        """Process a single job.

        Args:
            db: Database session
            job: Job to process
        """
        logger.info(f"Processing job {job.id} (type={job.job_type.value}, post={job.post_id})")

        # Mark as processing
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.attempts += 1
        db.commit()

        post = job.post

        if self.dry_run:
            logger.info(f"[DRY RUN] Would post to {post.platform.value}: {post.content[:100]}...")
            external_id = f"dry-run-{job.id}"
        else:
            # Execute based on job type
            if job.job_type == JobType.POST_TO_LINKEDIN:
                external_id = self._post_to_linkedin(db, post)
            elif job.job_type == JobType.POST_TO_TWITTER:
                external_id = self._post_to_twitter(db, post)
            elif job.job_type == JobType.POST_TO_BLOG:
                external_id = self._post_to_blog(db, post)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

        # Mark job as completed
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.last_error = None

        # Update post
        post.status = PostStatus.POSTED
        post.posted_at = datetime.utcnow()
        post.external_id = external_id

        db.commit()

        logger.info(f"Job {job.id} completed successfully (external_id={external_id})")

    def _post_to_linkedin(self, db, post: Post) -> str:
        """Post content to LinkedIn.

        Args:
            db: Database session
            post: Post to publish

        Returns:
            External post ID
        """
        # Get OAuth token
        stmt = select(OAuthToken).where(OAuthToken.platform == Platform.LINKEDIN)
        result = db.execute(stmt)
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            raise ValueError("No LinkedIn OAuth token found. Run OAuth flow first.")

        external_id = post_to_linkedin(
            content=post.content,
            access_token=oauth_token.access_token,
            user_sub=oauth_token.user_sub or "",
            dry_run=False,
        )

        return external_id

    def _post_to_twitter(self, db, post: Post) -> str:
        """Post content to Twitter/X.

        Args:
            db: Database session
            post: Post to publish

        Returns:
            External post ID
        """
        # TODO: Implement Twitter posting
        raise NotImplementedError("Twitter posting not yet implemented")

    def _post_to_blog(self, db, post: Post) -> str:
        """Post content to blog.

        Args:
            db: Database session
            post: Post to publish

        Returns:
            External post ID
        """
        # TODO: Implement blog posting
        raise NotImplementedError("Blog posting not yet implemented")

    def _handle_failure(self, db, job: JobQueue, error: str) -> None:
        """Handle job failure with retry logic.

        Args:
            db: Database session
            job: Failed job
            error: Error message
        """
        job.last_error = error

        if job.attempts >= job.max_attempts:
            # Max retries exceeded
            job.status = JobStatus.FAILED
            job.post.status = PostStatus.FAILED
            job.post.error_message = f"Max retries exceeded. Last error: {error}"
            logger.error(f"Job {job.id} failed permanently after {job.attempts} attempts")
        else:
            # Schedule retry with exponential backoff
            backoff_index = min(job.attempts - 1, len(self.RETRY_BACKOFF) - 1)
            backoff_seconds = self.RETRY_BACKOFF[backoff_index]
            job.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            job.status = JobStatus.PENDING  # Back to pending for retry

            logger.warning(
                f"Job {job.id} failed (attempt {job.attempts}/{job.max_attempts}), "
                f"retry in {backoff_seconds}s: {error}"
            )

        db.commit()

    def run_continuous(self, poll_interval: int = 30) -> None:
        """Run worker continuously, polling for new jobs.

        Args:
            poll_interval: Seconds between queue checks
        """
        logger.info(f"Starting continuous worker (poll_interval={poll_interval}s)")

        try:
            while True:
                processed = self.process_queue()
                if processed > 0:
                    logger.info(f"Processed {processed} jobs")

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")


def main() -> None:
    """Main entry point for job worker."""
    parser = argparse.ArgumentParser(description="ContentEngine Job Worker")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously (daemon mode)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without actually posting"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between queue checks in continuous mode (default: 30)"
    )

    args = parser.parse_args()

    worker = JobWorker(dry_run=args.dry_run)

    if args.continuous:
        worker.run_continuous(poll_interval=args.poll_interval)
    else:
        processed = worker.process_queue()
        print(f"Processed {processed} jobs")


if __name__ == "__main__":
    main()
