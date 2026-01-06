"""Web UI for Content Engine - FastAPI + HTMX 2.0."""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from lib.database import init_db, get_db, Post, PostStatus, Platform


# Initialize FastAPI app
app = FastAPI(title="Content Engine", description="AI-powered content posting system")

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="web/templates")


# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    db = get_db()

    # Get counts by status
    total_posts = db.execute(select(func.count(Post.id))).scalar()
    draft_count = db.execute(select(func.count(Post.id)).where(Post.status == PostStatus.DRAFT)).scalar()
    scheduled_count = db.execute(select(func.count(Post.id)).where(Post.status == PostStatus.SCHEDULED)).scalar()
    posted_count = db.execute(select(func.count(Post.id)).where(Post.status == PostStatus.POSTED)).scalar()

    # Get recent posts
    recent_posts = db.execute(
        select(Post).order_by(Post.created_at.desc()).limit(5)
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

    query = select(Post).order_by(Post.created_at.desc())

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
    db.close()

    if not post:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": f"Post {post_id} not found"
        }, status_code=404)

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

    query = select(Post).order_by(Post.created_at.desc())

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

    total_posts = db.execute(select(func.count(Post.id))).scalar()
    draft_count = db.execute(select(func.count(Post.id)).where(Post.status == PostStatus.DRAFT)).scalar()
    scheduled_count = db.execute(select(func.count(Post.id)).where(Post.status == PostStatus.SCHEDULED)).scalar()
    posted_count = db.execute(select(func.count(Post.id)).where(Post.status == PostStatus.POSTED)).scalar()

    db.close()

    return templates.TemplateResponse("components/stats.html", {
        "request": request,
        "total_posts": total_posts,
        "draft_count": draft_count,
        "scheduled_count": scheduled_count,
        "posted_count": posted_count,
    })


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
