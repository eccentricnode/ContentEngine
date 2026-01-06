"""Database models and session management for Content Engine."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


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


class Post(Base):
    """Content post model."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False, default=Platform.LINKEDIN)
    status = Column(SQLEnum(PostStatus), nullable=False, default=PostStatus.DRAFT)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)

    # External references
    external_id = Column(String(255), nullable=True)  # LinkedIn post ID, etc.
    error_message = Column(Text, nullable=True)

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
    """Initialize database (create tables if they don't exist)."""
    Base.metadata.create_all(engine)


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()
