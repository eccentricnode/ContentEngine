"""Authentication and session management for Content Engine."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session as DBSession

from lib.database import User, Session, get_db


# Session configuration
SESSION_COOKIE_NAME = "content_engine_session"
SESSION_DURATION_DAYS = 7


def create_session(user_id: int, db: DBSession) -> str:
    """Create a new session for a user.

    Args:
        user_id: User ID to create session for
        db: Database session

    Returns:
        Session ID (UUID)
    """
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DURATION_DAYS)

    session = Session(
        id=session_id,
        user_id=user_id,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()

    return session_id


def get_session(session_id: str, db: DBSession) -> Optional[Session]:
    """Get a session by ID.

    Args:
        session_id: Session ID to lookup
        db: Database session

    Returns:
        Session object if found and not expired, None otherwise
    """
    session = db.get(Session, session_id)

    if not session:
        return None

    # Check if expired
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        return None

    return session


def delete_session(session_id: str, db: DBSession) -> None:
    """Delete a session.

    Args:
        session_id: Session ID to delete
        db: Database session
    """
    session = db.get(Session, session_id)
    if session:
        db.delete(session)
        db.commit()


def get_user_from_request(request: Request) -> Optional[User]:
    """Get the current user from request cookies.

    Args:
        request: FastAPI request object

    Returns:
        User object if authenticated, None otherwise
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        return None

    db = get_db()
    session = get_session(session_id, db)

    if not session:
        db.close()
        return None

    user = db.get(User, session.user_id)
    db.close()

    return user


def set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie on response.

    Args:
        response: FastAPI response object
        session_id: Session ID to set in cookie
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_DURATION_DAYS * 24 * 60 * 60,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response.

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(key=SESSION_COOKIE_NAME)
