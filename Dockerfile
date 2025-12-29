# =============================================================================
# SetuPranali - Production Dockerfile
# =============================================================================
# Multi-stage build for minimal, secure production image.
#
# Build: docker build -t ubi-connector:latest .
# Run:   docker run -p 8080:8080 --env-file .env ubi-connector:latest
#
# Security features:
# - Non-root user (appuser)
# - Minimal base image (python:3.11-slim)
# - No development dependencies
# - Health check included
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
# Install dependencies in a separate stage to keep final image small.

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (cache layer)
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2: Production
# -----------------------------------------------------------------------------
# Minimal runtime image with only necessary files.

FROM python:3.11-slim AS production

# Labels for container metadata
LABEL maintainer="SetuPranali Team"
LABEL version="1.0.0"
LABEL description="Semantic analytics layer for BI tools"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
# Running as root in containers is a security risk
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser catalog.yaml ./

# Create directory for SQLite database with proper permissions
RUN mkdir -p /app/app/db && chown -R appuser:appuser /app/app/db

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Environment variables (defaults, override in docker-compose or .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

# Health check
# Checks /v1/health endpoint every 30 seconds
# Allows 5 seconds for startup, fails after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/v1/health || exit 1

# Run the application
# Using exec form to ensure proper signal handling
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

