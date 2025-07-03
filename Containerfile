# =============================================================================
# RAG OpenShift AI API - Containerfile
# =============================================================================
# Multi-stage build for production-ready container
# Optimized for OpenShift with security best practices

# =============================================================================
# Stage 1: Base Image with System Dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for OpenShift compatibility
RUN groupadd -r rag-api -g 1001 && \
    useradd -r -u 1001 -g rag-api -m -d /home/rag-api -s /bin/bash rag-api

# =============================================================================
# Stage 2: Python Dependencies
# =============================================================================
FROM base as dependencies

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Model Pre-loading
# =============================================================================
FROM dependencies as models

# Create models directory
RUN mkdir -p /opt/models && \
    chown -R rag-api:rag-api /opt/models

# Switch to non-root user
USER rag-api

# Set environment variable for model path
ENV SENTENCE_TRANSFORMERS_HOME=/opt/models

# Pre-download sentence-transformers model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# =============================================================================
# Stage 4: Application Code
# =============================================================================
FROM models as app

# Copy application source code
COPY --chown=rag-api:rag-api src/ ./src/
COPY --chown=rag-api:rag-api main.py .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R rag-api:rag-api /app

# =============================================================================
# Stage 5: Production Runtime
# =============================================================================
FROM app as production

# Switch back to root for final setup
USER root

# Create additional directories with proper permissions
RUN mkdir -p /app/tmp /app/cache && \
    chown -R rag-api:rag-api /app

# Switch to non-root user
USER rag-api

# Set working directory
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "main.py"]

# =============================================================================
# Stage 6: Development (optional)
# =============================================================================
FROM app as development

# Switch back to root for development setup
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    black \
    flake8 \
    mypy

# Switch to non-root user
USER rag-api

# Set working directory
WORKDIR /app

# Health check for development
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Development command with reload
CMD ["python", "main.py"] 