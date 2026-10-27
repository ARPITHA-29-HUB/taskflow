# Stage 1: Build dependencies in an isolated virtual environment
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Production runtime environment
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install runtime dependencies: curl for healthcheck, libpq5 for PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated unprivileged system user and group
RUN groupadd -r taskflow && useradd -r -g taskflow -u 10001 -d /app -s /sbin/nologin taskflow

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code, migrations, and Alembic configuration
COPY --chown=taskflow:taskflow alembic.ini .
COPY --chown=taskflow:taskflow app/ ./app/
COPY --chown=taskflow:taskflow migrations/ ./migrations/

# Drop to non-root user
USER taskflow

EXPOSE 8000

# Container healthcheck using FastAPI /health probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
