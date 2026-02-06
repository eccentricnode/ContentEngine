# Content Engine - Production Dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies (create venv in container)
RUN uv sync --frozen

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/context

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Run database migrations on startup
RUN uv run alembic upgrade head || true

# Expose port for API
EXPOSE 5000

# Default command (override in docker-compose.yml)
CMD ["uv", "run", "content-engine", "--help"]
