"""Database models and session management for Content Engine."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship


# Database path (SQLite file in project root)
DB_PATH = Path(__file__).parent.parent / "content.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class PostStatus(str, Enum):
    """Post status enum."""
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    REJECTED = "rejected"


class ContentPlanStatus(str, Enum):
    """Content plan status enum."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    GENERATED = "generated"
    CANCELLED = "cancelled"


class Platform(str, Enum):
    """Social media platform enum."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    BLOG = "blog"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    linkedin_sub = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    profile_picture_url = Column(String(1024), nullable=True)

    # OAuth tokens
    access_token = Column(String(1024), nullable=True)
    refresh_token = Column(String(1024), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Session(Base):
    """User session model."""

    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id})>"


class ChatMessage(Base):
    """Chat conversation history."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL = demo mode
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role})>"


class Post(Base):
    """Content post model."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False, default=Platform.LINKEDIN)
    status = Column(SQLEnum(PostStatus), nullable=False, default=PostStatus.DRAFT)

    # User ownership (NULL = demo post by Austin)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)

    # External references
    external_id = Column(String(255), nullable=True)  # LinkedIn post ID, etc.
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="posts")

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, platform={self.platform}, status={self.status})>"


class Blueprint(Base):
    """Blueprint cache model for storing loaded blueprints."""

    __tablename__ = "blueprints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # framework, workflow, constraint
    platform = Column(String(50), nullable=True)  # linkedin, twitter, blog (NULL for non-framework)
    data = Column(JSON, nullable=False)  # Parsed YAML data as JSON
    version = Column(String(50), nullable=True)  # Optional versioning
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Blueprint(id={self.id}, name={self.name}, category={self.category})>"


class OAuthToken(Base):
    """OAuth token storage."""

    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(SQLEnum(Platform), nullable=False, unique=True)
    access_token = Column(String(1024), nullable=False)
    refresh_token = Column(String(1024), nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # User info
    user_sub = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<OAuthToken(platform={self.platform})>"


class ContentPlan(Base):
    """Content plan model for workflow-generated content ideas."""

    __tablename__ = "content_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start_date = Column(String(10), nullable=False)  # YYYY-MM-DD format
    pillar = Column(String(50), nullable=False)  # what_building, what_learning, etc.
    framework = Column(String(50), nullable=False)  # STF, MRS, SLA, PIF
    idea = Column(Text, nullable=False)  # Content idea/title
    status = Column(SQLEnum(ContentPlanStatus), nullable=False, default=ContentPlanStatus.PLANNED)

    # Brand Planner fields (Phase 4)
    game = Column(String(30), nullable=True)  # traffic / building_in_public
    hook_type = Column(String(30), nullable=True)  # problem_first, shipped, etc.
    core_insight = Column(Text, nullable=True)  # One-sentence insight
    context_summary = Column(Text, nullable=True)  # Relevant context for generation
    structure_preview = Column(Text, nullable=True)  # Expected post structure
    rationale = Column(Text, nullable=True)  # Why these choices
    source_theme = Column(String(255), nullable=True)  # Original context theme
    audience_value = Column(String(20), nullable=True)  # low/medium/high

    # Optional: link to generated post
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("Post", foreign_keys=[post_id])

    def __repr__(self) -> str:
        return f"<ContentPlan(id={self.id}, pillar={self.pillar}, framework={self.framework}, status={self.status})>"


class JobStatus(str, Enum):
    """Job queue status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type enum."""
    POST_TO_LINKEDIN = "post_to_linkedin"
    POST_TO_TWITTER = "post_to_twitter"
    POST_TO_BLOG = "post_to_blog"


class JobQueue(Base):
    """SQLite-based job queue for scheduled content posting."""

    __tablename__ = "job_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)

    # Reference to content
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)  # NULL = immediate
    priority = Column(Integer, default=0)  # Higher = more urgent

    # Retry handling
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Tracking
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Source tracking (for edit-after-ingest)
    source_file = Column(String(512), nullable=True)  # Path in git worktree
    source_hash = Column(String(64), nullable=True)  # Content hash for change detection

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("Post", foreign_keys=[post_id])

    def __repr__(self) -> str:
        return f"<JobQueue(id={self.id}, type={self.job_type}, status={self.status}, post_id={self.post_id})>"


def init_db() -> None:
    """Initialize database (create tables if they don't exist).

    WARNING: This function is deprecated and kept for backwards compatibility.
    Use Alembic migrations instead:
        uv run alembic upgrade head

    This function will be removed in a future version.
    """
    import warnings
    warnings.warn(
        "init_db() is deprecated. Use Alembic migrations: uv run alembic upgrade head",
        DeprecationWarning,
        stacklevel=2
    )
    Base.metadata.create_all(engine)


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()
