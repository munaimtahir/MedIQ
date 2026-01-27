# Multi-stage production Dockerfile for FastAPI backend
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

# Install curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set PATH to include user local bin
ENV PATH=/home/appuser/.local/bin:$PATH

# Set Python to not buffer output (better for containers)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Production environment variables
ENV ENV=prod
ENV UVICORN_WORKERS=${UVICORN_WORKERS:-5}
ENV UVICORN_TIMEOUT_KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-5}
ENV UVICORN_LIMIT_CONCURRENCY=${UVICORN_LIMIT_CONCURRENCY:-200}
ENV UVICORN_LIMIT_MAX_REQUESTS=${UVICORN_LIMIT_MAX_REQUESTS:-10000}

# Expose internal port (not exposed to host - accessed via Traefik)
EXPOSE 8000

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# OCI labels for metadata
LABEL org.opencontainers.image.source="https://github.com/your-org/exam-prep-platform" \
      org.opencontainers.image.revision="${GITHUB_SHA:-unknown}" \
      org.opencontainers.image.created="${BUILD_DATE:-unknown}" \
      org.opencontainers.image.title="Exam Prep Platform Backend" \
      org.opencontainers.image.description="FastAPI backend for medical exam practice platform"

# Production command: uvicorn with workers
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS} --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE} --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY} --limit-max-requests ${UVICORN_LIMIT_MAX_REQUESTS}"]
