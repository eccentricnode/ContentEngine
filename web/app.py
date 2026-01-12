"""Web UI for Content Engine - FastAPI + HTMX 2.0."""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import requests

from fastapi import FastAPI, Request, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from lib.database import init_db, get_db, Post, PostStatus, Platform, User
from lib.ollama import get_ollama_client
from lib.errors import AIError
from lib.config import get_linkedin_config
from lib.auth import create_session, delete_session, set_session_cookie, clear_session_cookie
from lib.middleware import UserContextMiddleware


# Initialize FastAPI app
app = FastAPI(title="Content Engine", description="AI-powered content posting system")

# Add middleware (user context injection)
app.add_middleware(UserContextMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="web/templates")


# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()
    cleanup_old_posts()


# OAuth state storage (in-memory for now)
oauth_states = {}


@app.get("/auth/linkedin")
async def auth_linkedin(request: Request):
    """Redirect to LinkedIn OAuth authorization."""
    config = get_linkedin_config()

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True  # Store state

    # Build LinkedIn authorization URL
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={config.client_id}"
        f"&redirect_uri={config.redirect_uri}"
        f"&state={state}"
        f"&scope=openid profile email"
    )

    return RedirectResponse(auth_url)


@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle LinkedIn OAuth callback."""
    config = get_linkedin_config()

    # Verify state (CSRF protection)
    if state not in oauth_states:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "Invalid OAuth state. Please try again."
        }, status_code=400)

    # Remove state (one-time use)
    del oauth_states[state]

    try:
        # Exchange code for access token
        token_response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.redirect_uri,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        access_token = token_data["access_token"]

        # Get user profile
        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()

        # Create or update user
        db = get_db()
        user = db.query(User).filter(User.linkedin_sub == profile["sub"]).first()

        if not user:
            # Create new user
            user = User(
                linkedin_sub=profile["sub"],
                email=profile.get("email"),
                name=profile.get("name"),
                profile_picture_url=profile.get("picture"),
                access_token=access_token,
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
        else:
            # Update existing user
            user.access_token = access_token
            user.last_login_at = datetime.utcnow()
            if profile.get("email"):
                user.email = profile.get("email")
            if profile.get("name"):
                user.name = profile.get("name")
            if profile.get("picture"):
                user.profile_picture_url = profile.get("picture")

        db.commit()
        user_id = user.id
        db.close()

        # Create session
        db = get_db()
        session_id = create_session(user_id, db)
        db.close()

        # Set session cookie and redirect to dashboard
        response = RedirectResponse("/", status_code=302)
        set_session_cookie(response, session_id)

        return response

    except requests.RequestException as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": f"OAuth failed: {e}"
        }, status_code=500)


@app.get("/auth/logout")
async def auth_logout(request: Request):
    """Log out and clear session."""
    session_id = request.cookies.get("content_engine_session")

    if session_id:
        db = get_db()
        delete_session(session_id, db)
        db.close()

    response = RedirectResponse("/", status_code=302)
    clear_session_cookie(response)

    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    db = get_db()

    # Filter posts based on auth mode
    user = request.state.user
    if user:
        # Authenticated: Show user's own posts
        base_query = select(Post).where(Post.user_id == user.id)
    else:
        # Demo mode: Show only demo posts
        base_query = select(Post).where(Post.is_demo == True)

    # Get counts by status
    total_posts = db.execute(select(func.count(Post.id)).select_from(base_query.subquery())).scalar()

    draft_count = db.execute(
        select(func.count(Post.id)).select_from(
            base_query.where(Post.status == PostStatus.DRAFT).subquery()
        )
    ).scalar()

    scheduled_count = db.execute(
        select(func.count(Post.id)).select_from(
            base_query.where(Post.status == PostStatus.SCHEDULED).subquery()
        )
    ).scalar()

    posted_count = db.execute(
        select(func.count(Post.id)).select_from(
            base_query.where(Post.status == PostStatus.POSTED).subquery()
        )
    ).scalar()

    # Get recent posts
    recent_posts = db.execute(
        base_query.order_by(Post.created_at.desc()).limit(5)
    ).scalars().all()

    db.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_posts": total_posts,
        "draft_count": draft_count,
        "scheduled_count": scheduled_count,
        "posted_count": posted_count,
        "recent_posts": recent_posts,
    })


@app.get("/posts", response_class=HTMLResponse)
async def posts_list(
    request: Request,
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
):
    """List posts with optional filtering."""
    db = get_db()

    # Filter by user/demo mode
    user = request.state.user
    if user:
        query = select(Post).where(Post.user_id == user.id)
    else:
        query = select(Post).where(Post.is_demo == True)

    query = query.order_by(Post.created_at.desc())

    if status:
        query = query.where(Post.status == PostStatus(status))
    if platform:
        query = query.where(Post.platform == Platform(platform))

    posts = db.execute(query).scalars().all()
    db.close()

    return templates.TemplateResponse("posts_list.html", {
        "request": request,
        "posts": posts,
        "current_status": status,
        "current_platform": platform,
    })


@app.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: int):
    """Show full post details."""
    db = get_db()

    post = db.get(Post, post_id)

    if not post:
        db.close()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": f"Post {post_id} not found"
        }, status_code=404)

    # Verify ownership
    user = request.state.user
    if user:
        # Authenticated: Only show user's own posts
        if post.user_id != user.id:
            db.close()
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "Unauthorized"
            }, status_code=403)
    else:
        # Demo mode: Only show demo posts
        if not post.is_demo:
            db.close()
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "Unauthorized"
            }, status_code=403)

    db.close()

    return templates.TemplateResponse("post_detail.html", {
        "request": request,
        "post": post,
    })


@app.get("/api/posts", response_class=HTMLResponse)
async def api_posts(
    request: Request,
    status: Optional[str] = Query(None),
):
    """API endpoint for HTMX to load posts dynamically."""
    db = get_db()

    # Filter by user/demo mode
    user = request.state.user
    if user:
        query = select(Post).where(Post.user_id == user.id)
    else:
        query = select(Post).where(Post.is_demo == True)

    query = query.order_by(Post.created_at.desc())

    if status:
        query = query.where(Post.status == PostStatus(status))

    posts = db.execute(query).scalars().all()
    db.close()

    return templates.TemplateResponse("components/post_list.html", {
        "request": request,
        "posts": posts,
    })


@app.get("/api/stats", response_class=HTMLResponse)
async def api_stats(request: Request):
    """API endpoint for live stats."""
    db = get_db()

    # Filter by user/demo mode
    user = request.state.user
    if user:
        base_query = select(Post).where(Post.user_id == user.id)
    else:
        base_query = select(Post).where(Post.is_demo == True)

    # Get counts
    total_posts = db.execute(select(func.count(Post.id)).select_from(base_query.subquery())).scalar()

    draft_count = db.execute(
        select(func.count(Post.id)).select_from(
            base_query.where(Post.status == PostStatus.DRAFT).subquery()
        )
    ).scalar()

    scheduled_count = db.execute(
        select(func.count(Post.id)).select_from(
            base_query.where(Post.status == PostStatus.SCHEDULED).subquery()
        )
    ).scalar()

    posted_count = db.execute(
        select(func.count(Post.id)).select_from(
            base_query.where(Post.status == PostStatus.POSTED).subquery()
        )
    ).scalar()

    db.close()

    return templates.TemplateResponse("components/stats.html", {
        "request": request,
        "total_posts": total_posts,
        "draft_count": draft_count,
        "scheduled_count": scheduled_count,
        "posted_count": posted_count,
    })


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI chat interface for content ideation."""
    return templates.TemplateResponse("chat.html", {
        "request": request,
    })


@app.post("/chat/message", response_class=HTMLResponse)
async def chat_message(request: Request):
    """Handle chat message and return AI response."""
    form_data = await request.form()
    user_message = form_data.get("message", "").strip()

    if not user_message:
        return templates.TemplateResponse("components/chat_error.html", {
            "request": request,
            "error": "Please enter a message"
        })

    try:
        ollama = get_ollama_client()
        ai_response = ollama.generate_content_ideas(user_message)

        return templates.TemplateResponse("components/chat_messages.html", {
            "request": request,
            "user_message": user_message,
            "ai_response": ai_response,
        })
    except AIError as e:
        return templates.TemplateResponse("components/chat_error.html", {
            "request": request,
            "error": str(e)
        })


@app.post("/chat/draft", response_class=HTMLResponse)
async def draft_from_chat(request: Request):
    """Create a draft post from AI-suggested content."""
    form_data = await request.form()
    content = form_data.get("content", "").strip()

    if not content:
        return "<p style='color: red;'>No content provided</p>"

    # Check authentication
    user = request.state.user

    if not user:
        # Demo mode: Don't persist, show message
        return """
        <div style='background: #fef3c7; color: #92400e; padding: 1rem; border-radius: 8px; margin-top: 1rem;'>
            👋 <strong>This is demo mode!</strong>
            <a href='/auth/linkedin' style='color: #92400e; text-decoration: underline;'>Sign in with LinkedIn</a>
            to save drafts permanently.
        </div>
        """

    # Authenticated: Save to database
    db = get_db()
    post = Post(
        content=content,
        platform=Platform.LINKEDIN,
        status=PostStatus.DRAFT,
        user_id=user.id,
        is_demo=False,
    )
    db.add(post)
    db.commit()
    post_id = post.id
    db.close()

    return f"""
    <div style='background: #dcfce7; color: #166534; padding: 1rem; border-radius: 8px; margin-top: 1rem;'>
        ✅ Draft created (ID: {post_id})! <a href='/posts/{post_id}' style='color: #166534; text-decoration: underline;'>View post →</a>
    </div>
    """


# Post Action Routes (Auth-Gated)
@app.post("/posts/{post_id}/approve")
async def approve_post(request: Request, post_id: int):
    """Approve a draft and mark as posted."""
    user = request.state.user
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    db = get_db()
    post = db.get(Post, post_id)

    if not post:
        db.close()
        return JSONResponse({"error": "Post not found"}, status_code=404)

    if post.user_id != user.id:
        db.close()
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    post.status = PostStatus.POSTED
    post.posted_at = datetime.utcnow()
    db.commit()
    db.close()

    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/posts/{post_id}/schedule")
async def schedule_post(request: Request, post_id: int):
    """Schedule a post for later."""
    user = request.state.user
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    db = get_db()
    post = db.get(Post, post_id)

    if not post:
        db.close()
        return JSONResponse({"error": "Post not found"}, status_code=404)

    if post.user_id != user.id:
        db.close()
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    # For now, schedule for 1 day from now
    post.status = PostStatus.SCHEDULED
    post.scheduled_at = datetime.utcnow() + timedelta(days=1)
    db.commit()
    db.close()

    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/posts/{post_id}/post-now")
async def post_now(request: Request, post_id: int):
    """Post a scheduled post immediately."""
    user = request.state.user
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    db = get_db()
    post = db.get(Post, post_id)

    if not post:
        db.close()
        return JSONResponse({"error": "Post not found"}, status_code=404)

    if post.user_id != user.id:
        db.close()
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    # TODO: Actually post to LinkedIn API here
    post.status = PostStatus.POSTED
    post.posted_at = datetime.utcnow()
    db.commit()
    db.close()

    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.delete("/posts/{post_id}")
async def delete_post(request: Request, post_id: int):
    """Delete a post."""
    user = request.state.user
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    db = get_db()
    post = db.get(Post, post_id)

    if not post:
        db.close()
        return JSONResponse({"error": "Post not found"}, status_code=404)

    if post.user_id != user.id:
        db.close()
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    db.delete(post)
    db.commit()
    db.close()

    return HTMLResponse("", status_code=200)


@app.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_form(request: Request, post_id: int):
    """Show edit form for a post."""
    user = request.state.user
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    db = get_db()
    post = db.get(Post, post_id)

    if not post:
        db.close()
        return JSONResponse({"error": "Post not found"}, status_code=404)

    if post.user_id != user.id:
        db.close()
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    db.close()

    # Return inline edit form
    return f"""
    <form hx-post="/posts/{post_id}/edit" hx-swap="outerHTML" style="margin-top: 1rem;">
        <textarea name="content" rows="10" style="width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px;">{post.content}</textarea>
        <div style="margin-top: 1rem;">
            <button type="submit" class="btn-primary">💾 Save Changes</button>
            <button type="button" onclick="window.location.reload()" class="btn-secondary">Cancel</button>
        </div>
    </form>
    """


@app.post("/posts/{post_id}/edit")
async def save_post_edit(request: Request, post_id: int):
    """Save post edits."""
    user = request.state.user
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    form_data = await request.form()
    new_content = form_data.get("content", "").strip()

    if not new_content:
        return HTMLResponse("<p style='color: red;'>Content cannot be empty</p>", status_code=400)

    db = get_db()
    post = db.get(Post, post_id)

    if not post:
        db.close()
        return JSONResponse({"error": "Post not found"}, status_code=404)

    if post.user_id != user.id:
        db.close()
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    post.content = new_content
    db.commit()
    db.close()

    return RedirectResponse(f"/posts/{post_id}", status_code=303)


# Jinja2 filters for templates
@app.on_event("startup")
def add_jinja_filters():
    """Add custom Jinja2 filters."""
    def format_datetime(value: datetime, format: str = "%Y-%m-%d %H:%M") -> str:
        if value is None:
            return ""
        return value.strftime(format)

    def status_badge_class(status: PostStatus) -> str:
        """Return CSS class for status badge."""
        mapping = {
            PostStatus.DRAFT: "badge-draft",
            PostStatus.APPROVED: "badge-approved",
            PostStatus.SCHEDULED: "badge-scheduled",
            PostStatus.POSTED: "badge-posted",
            PostStatus.FAILED: "badge-failed",
            PostStatus.REJECTED: "badge-rejected",
        }
        return mapping.get(status, "badge-default")

    def truncate(text: str, length: int = 100) -> str:
        """Truncate text to length."""
        if len(text) <= length:
            return text
        return text[:length] + "..."

    templates.env.filters["format_datetime"] = format_datetime
    templates.env.filters["status_badge_class"] = status_badge_class
    templates.env.filters["truncate"] = truncate


def cleanup_old_posts():
    """Delete posts older than 5 minutes (for demo purposes)."""
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)

    deleted_count = db.query(Post).filter(Post.created_at < cutoff_time).delete()

    if deleted_count > 0:
        db.commit()
        print(f"🗑️  Cleaned up {deleted_count} posts older than 5 minutes")

    db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
