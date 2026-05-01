# ═══════════════════════════════════════════════════════════════
# CySec Don SQLi Training Lab - Dockerfile
# ═══════════════════════════════════════════════════════════════
# Multi-stage build for minimal final image
# Build:   docker build -t cysec-lab .
# Run:     docker run --rm -p 5000:5000 --name cysec-lab cysec-lab
# NOTE:    Requires external MySQL/MariaDB. Use docker-compose for full stack.
# ═══════════════════════════════════════════════════════════════

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

LABEL maintainer="CySec Don <cysecdon@gmail.com>"
LABEL description="CySec Don SQLi Training Lab - Intentionally vulnerable web app for security education"
LABEL warning="EDUCATIONAL USE ONLY - Never deploy on public networks"

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-mysql-client && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Create app user
RUN groupadd -r cysec && useradd -r -g cysec -d /app -s /sbin/nologin cysec

# Copy application
WORKDIR /app
COPY --chown=cysec:cysec app/ ./app/
COPY --chown=cysec:cysec db/ ./db/

# Environment variables (defaults for Docker)
ENV FLASK_SECRET_KEY=cysec-lab-docker-change-me
ENV DB_HOST=db
ENV DB_PORT=3306
ENV DB_USER=cysec_lab
ENV DB_PASSWORD=cysec_lab_pass
ENV DB_NAME=cysec_lab
ENV SECURITY_LEVEL=low
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Run as non-root user
USER cysec

CMD ["python", "-m", "app.main"]
