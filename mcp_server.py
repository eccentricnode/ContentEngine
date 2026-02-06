"""MCP Server for ContentEngine.

Exposes ContentEngine functionality to Claude Code via Model Context Protocol.
Run on-demand when needed, not as a persistent service.

Usage:
    uv run python mcp_server.py
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from lib.database import (
    get_db,
    Post,
    PostStatus,
    Platform,
    ContentPlan,
    ContentPlanStatus,
    JobQueue,
    JobStatus,
    JobType,
    OAuthToken,
)
from lib.logger import setup_logger

logger = setup_logger(__name__)


class ContentEngineMCP:
    """MCP server exposing ContentEngine operations."""

    def __init__(self) -> None:
        """Initialize MCP server."""
        self.tools = {
            "ingest": self.ingest,
            "schedule": self.schedule,
            "fire": self.fire,  # Immediate post
            "cancel": self.cancel,
            "status": self.status,
            "list_pending": self.list_pending,
            "list_scheduled": self.list_scheduled,
            "sync": self.sync,  # Re-sync from source file
        }

    def handle_request(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming MCP request.

        Args:
            tool: Tool name to invoke
            params: Parameters for the tool

        Returns:
            Response dictionary
        """
        if tool not in self.tools:
            return {"error": f"Unknown tool: {tool}", "available": list(self.tools.keys())}

        try:
            result = self.tools[tool](**params)
            return {"success": True, "result": result}
        except Exception as e:
            logger.exception(f"Tool {tool} failed")
            return {"success": False, "error": str(e)}

    def ingest(
        self,
        content: str,
        platform: str = "linkedin",
        source_file: Optional[str] = None,
        pillar: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> dict[str, Any]:
        """Ingest content into ContentEngine.

        Creates a Post in APPROVED state, ready for scheduling.
        If source_file provided, tracks for edit-after-ingest handling.

        Args:
            content: The post content
            platform: Target platform (linkedin, twitter, blog)
            source_file: Optional path to source file for change tracking
            pillar: Optional content pillar
            framework: Optional framework used

        Returns:
            Dict with post_id and status
        """
        db = get_db()

        # Calculate content hash for change detection
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Check for duplicate (same source file)
        if source_file:
            existing = db.query(JobQueue).filter(
                JobQueue.source_file == source_file,
                JobQueue.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])
            ).first()

            if existing:
                # Update existing instead of creating duplicate
                existing_post = existing.post
                existing_post.content = content
                existing_post.updated_at = datetime.utcnow()
                existing.source_hash = content_hash
                existing.updated_at = datetime.utcnow()
                db.commit()

                logger.info(f"Updated existing post {existing_post.id} from {source_file}")
                return {
                    "action": "updated",
                    "post_id": existing_post.id,
                    "job_id": existing.id,
                    "message": "Existing post updated with new content",
                }

        # Create new post
        post = Post(
            content=content,
            platform=Platform(platform),
            status=PostStatus.APPROVED,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        logger.info(f"Ingested new post {post.id} for {platform}")

        return {
            "action": "created",
            "post_id": post.id,
            "platform": platform,
            "content_hash": content_hash,
            "source_file": source_file,
            "message": "Content ingested and approved",
        }

    def schedule(
        self,
        post_id: int,
        scheduled_at: str,
        priority: int = 0,
        source_file: Optional[str] = None,
    ) -> dict[str, Any]:
        """Schedule a post for future publishing.

        Args:
            post_id: ID of the post to schedule
            scheduled_at: ISO format datetime string (e.g., "2026-02-10T09:00:00")
            priority: Job priority (higher = more urgent)
            source_file: Optional source file path for tracking

        Returns:
            Dict with job_id and scheduled time
        """
        db = get_db()

        post = db.get(Post, post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        if post.status not in [PostStatus.APPROVED, PostStatus.DRAFT]:
            raise ValueError(f"Post must be APPROVED or DRAFT, got {post.status.value}")

        # Parse scheduled time
        try:
            schedule_time = datetime.fromisoformat(scheduled_at)
        except ValueError:
            raise ValueError(f"Invalid datetime format: {scheduled_at}. Use ISO format.")

        if schedule_time < datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")

        # Determine job type based on platform
        job_type_map = {
            Platform.LINKEDIN: JobType.POST_TO_LINKEDIN,
            Platform.TWITTER: JobType.POST_TO_TWITTER,
            Platform.BLOG: JobType.POST_TO_BLOG,
        }
        job_type = job_type_map[post.platform]

        # Calculate content hash
        content_hash = hashlib.sha256(post.content.encode()).hexdigest()[:16]

        # Check for existing job for this post
        existing_job = db.query(JobQueue).filter(
            JobQueue.post_id == post_id,
            JobQueue.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])
        ).first()

        if existing_job:
            # Update existing job
            existing_job.scheduled_at = schedule_time
            existing_job.priority = priority
            existing_job.source_hash = content_hash
            if source_file:
                existing_job.source_file = source_file
            existing_job.updated_at = datetime.utcnow()
            db.commit()

            return {
                "action": "rescheduled",
                "job_id": existing_job.id,
                "post_id": post_id,
                "scheduled_at": schedule_time.isoformat(),
            }

        # Create new job
        job = JobQueue(
            job_type=job_type,
            status=JobStatus.PENDING,
            post_id=post_id,
            scheduled_at=schedule_time,
            priority=priority,
            source_file=source_file,
            source_hash=content_hash,
        )
        db.add(job)

        # Update post status
        post.status = PostStatus.SCHEDULED
        post.scheduled_at = schedule_time

        db.commit()
        db.refresh(job)

        logger.info(f"Scheduled job {job.id} for post {post_id} at {schedule_time}")

        return {
            "action": "scheduled",
            "job_id": job.id,
            "post_id": post_id,
            "scheduled_at": schedule_time.isoformat(),
            "platform": post.platform.value,
        }

    def fire(self, post_id: int) -> dict[str, Any]:
        """Immediately post content (bypass queue).

        Args:
            post_id: ID of the post to publish immediately

        Returns:
            Dict with job_id and status
        """
        db = get_db()

        post = db.get(Post, post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        # Determine job type
        job_type_map = {
            Platform.LINKEDIN: JobType.POST_TO_LINKEDIN,
            Platform.TWITTER: JobType.POST_TO_TWITTER,
            Platform.BLOG: JobType.POST_TO_BLOG,
        }
        job_type = job_type_map[post.platform]

        # Create high-priority job with no scheduled time (immediate)
        job = JobQueue(
            job_type=job_type,
            status=JobStatus.PENDING,
            post_id=post_id,
            scheduled_at=None,  # NULL = immediate
            priority=100,  # High priority
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"Created immediate job {job.id} for post {post_id}")

        return {
            "action": "queued_immediate",
            "job_id": job.id,
            "post_id": post_id,
            "message": "Post queued for immediate publishing. Run worker to process.",
        }

    def cancel(self, job_id: Optional[int] = None, post_id: Optional[int] = None) -> dict[str, Any]:
        """Cancel a scheduled job.

        Args:
            job_id: ID of the job to cancel (preferred)
            post_id: ID of the post whose jobs to cancel

        Returns:
            Dict with cancellation status
        """
        db = get_db()

        if job_id:
            job = db.get(JobQueue, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            if job.status not in [JobStatus.PENDING]:
                raise ValueError(f"Can only cancel PENDING jobs, got {job.status.value}")

            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.utcnow()

            # Revert post status
            post = job.post
            post.status = PostStatus.APPROVED
            post.scheduled_at = None

            db.commit()

            return {
                "action": "cancelled",
                "job_id": job_id,
                "post_id": post.id,
            }

        elif post_id:
            jobs = db.query(JobQueue).filter(
                JobQueue.post_id == post_id,
                JobQueue.status == JobStatus.PENDING
            ).all()

            if not jobs:
                return {"action": "none", "message": "No pending jobs found for this post"}

            cancelled_ids = []
            for job in jobs:
                job.status = JobStatus.CANCELLED
                job.updated_at = datetime.utcnow()
                cancelled_ids.append(job.id)

            # Revert post status
            post = db.get(Post, post_id)
            if post:
                post.status = PostStatus.APPROVED
                post.scheduled_at = None

            db.commit()

            return {
                "action": "cancelled",
                "cancelled_jobs": cancelled_ids,
                "post_id": post_id,
            }

        else:
            raise ValueError("Must provide either job_id or post_id")

    def status(self, job_id: Optional[int] = None, post_id: Optional[int] = None) -> dict[str, Any]:
        """Get status of a job or post.

        Args:
            job_id: ID of job to check
            post_id: ID of post to check

        Returns:
            Status information
        """
        db = get_db()

        if job_id:
            job = db.get(JobQueue, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            return {
                "job_id": job.id,
                "job_type": job.job_type.value,
                "status": job.status.value,
                "post_id": job.post_id,
                "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "last_error": job.last_error,
                "created_at": job.created_at.isoformat(),
            }

        elif post_id:
            post = db.get(Post, post_id)
            if not post:
                raise ValueError(f"Post {post_id} not found")

            jobs = db.query(JobQueue).filter(JobQueue.post_id == post_id).all()

            return {
                "post_id": post.id,
                "post_status": post.status.value,
                "platform": post.platform.value,
                "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
                "posted_at": post.posted_at.isoformat() if post.posted_at else None,
                "jobs": [
                    {
                        "job_id": j.id,
                        "status": j.status.value,
                        "scheduled_at": j.scheduled_at.isoformat() if j.scheduled_at else None,
                    }
                    for j in jobs
                ],
            }

        else:
            raise ValueError("Must provide either job_id or post_id")

    def list_pending(self, limit: int = 20) -> dict[str, Any]:
        """List pending jobs in the queue.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of pending jobs
        """
        db = get_db()

        jobs = db.query(JobQueue).filter(
            JobQueue.status == JobStatus.PENDING
        ).order_by(
            JobQueue.priority.desc(),
            JobQueue.scheduled_at.asc()
        ).limit(limit).all()

        return {
            "count": len(jobs),
            "jobs": [
                {
                    "job_id": j.id,
                    "post_id": j.post_id,
                    "job_type": j.job_type.value,
                    "scheduled_at": j.scheduled_at.isoformat() if j.scheduled_at else "immediate",
                    "priority": j.priority,
                    "source_file": j.source_file,
                }
                for j in jobs
            ],
        }

    def list_scheduled(self, days_ahead: int = 7) -> dict[str, Any]:
        """List scheduled posts for the next N days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of scheduled posts
        """
        db = get_db()

        cutoff = datetime.utcnow() + timedelta(days=days_ahead)

        jobs = db.query(JobQueue).filter(
            JobQueue.status == JobStatus.PENDING,
            JobQueue.scheduled_at.isnot(None),
            JobQueue.scheduled_at <= cutoff
        ).order_by(JobQueue.scheduled_at.asc()).all()

        return {
            "days_ahead": days_ahead,
            "count": len(jobs),
            "scheduled": [
                {
                    "job_id": j.id,
                    "post_id": j.post_id,
                    "platform": j.post.platform.value,
                    "scheduled_at": j.scheduled_at.isoformat(),
                    "content_preview": j.post.content[:100] + "..." if len(j.post.content) > 100 else j.post.content,
                }
                for j in jobs
            ],
        }

    def sync(self, source_file: str, content: str) -> dict[str, Any]:
        """Sync content from source file (edit-after-ingest handling).

        Checks if content has changed and updates if necessary.

        Args:
            source_file: Path to the source file
            content: Current content of the file

        Returns:
            Sync result
        """
        db = get_db()

        # Calculate new hash
        new_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Find job with this source file
        job = db.query(JobQueue).filter(
            JobQueue.source_file == source_file,
            JobQueue.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])
        ).first()

        if not job:
            return {
                "action": "not_found",
                "source_file": source_file,
                "message": "No pending job found for this source file",
            }

        # Check if content changed
        if job.source_hash == new_hash:
            return {
                "action": "unchanged",
                "job_id": job.id,
                "post_id": job.post_id,
                "message": "Content unchanged",
            }

        # Update content
        job.post.content = content
        job.post.updated_at = datetime.utcnow()
        job.source_hash = new_hash
        job.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Synced post {job.post_id} from {source_file}")

        return {
            "action": "updated",
            "job_id": job.id,
            "post_id": job.post_id,
            "old_hash": job.source_hash,
            "new_hash": new_hash,
            "message": "Content updated from source file",
        }


# CLI interface for testing
if __name__ == "__main__":
    import sys

    mcp = ContentEngineMCP()

    if len(sys.argv) < 2:
        print("Usage: python mcp_server.py <tool> [params_json]")
        print(f"Available tools: {list(mcp.tools.keys())}")
        sys.exit(1)

    tool = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    result = mcp.handle_request(tool, params)
    print(json.dumps(result, indent=2, default=str))
