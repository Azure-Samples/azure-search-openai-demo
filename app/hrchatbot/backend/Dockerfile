FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Create app directory
WORKDIR /app

# Copy essential project files
# Copy dependency files
COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock

# Install dependencies with uv (creates .venv)
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Ensure we use the venv
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
EXPOSE 8000
CMD ["python", "-m", "gunicorn", "-b", "0.0.0.0:8000", "main:app"]
