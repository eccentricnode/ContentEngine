"""Database models and session management for Content Engine."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship


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
