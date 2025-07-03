# =============================================================================
# RAG OpenShift AI API - Containerfile
# =============================================================================
# Multi-stage build for production-ready container
# Optimized for OpenShift 4.18+ with security best practices

# =============================================================================
# Stage 1: Base Image with System Dependencies
# =============================================================================
FROM registry.access.redhat.com/ubi9/python-311:1-209 as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Install system dependencies for OpenShift compatibility
RUN microdnf update -y && \
    microdnf install -y \
    curl \
    gcc \
    gcc-c++ \
    make \
    && microdnf clean all

# Create non-root user for OpenShift compatibility (UID 1001)
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
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Model Pre-loading
# =============================================================================
FROM dependencies as models

# Create models directory with proper permissions
RUN mkdir -p /opt/models && \
    chown -R rag-api:rag-api /opt/models

# Switch to non-root user
USER rag-api

# Set environment variable for model path
ENV SENTENCE_TRANSFORMERS_HOME=/opt/models \
    TRANSFORMERS_CACHE=/opt/models \
    HF_HOME=/opt/models

# Pre-download sentence-transformers model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# =============================================================================
# Stage 4: Application Code
# =============================================================================
FROM models as app

# Copy application source code
COPY --chown=rag-api:rag-api src/ ./src/
COPY --chown=rag-api:rag-api main.py .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/tmp /app/cache && \
    chown -R rag-api:rag-api /app

# =============================================================================
# Stage 5: Production Runtime
# =============================================================================
FROM app as production

# Switch back to root for final setup
USER root

# Create additional directories with proper permissions
RUN mkdir -p /app/tmp /app/cache /app/uploads && \
    chown -R rag-api:rag-api /app && \
    chmod -R 755 /app

# Switch to non-root user
USER rag-api

# Set working directory
WORKDIR /app

# Health check optimized for OpenShift
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
    pytest-cov \
    black \
    flake8 \
    mypy \
    pre-commit

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