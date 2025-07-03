# =============================================================================
# RAG OpenShift AI API - Dockerfile
# =============================================================================
# Optimized for OpenShift 4.18+ with Red Hat UBI 9 Python 3.11
# This file is identical to Containerfile for compatibility

# Use Red Hat UBI 9 Python 3.11 as base image (OpenShift 4.18+ optimized)
FROM registry.access.redhat.com/ubi9/python-311:latest

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies (OpenShift 4.18+ security optimized)
RUN microdnf update -y && \
    microdnf install -y \
        gcc \
        gcc-c++ \
        make \
        curl \
        ca-certificates \
        openssl \
        && \
    microdnf clean all && \
    rm -rf /var/cache/yum

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Create non-root user for security (OpenShift 4.18+ requirement)
RUN groupadd -r raguser -g 1001 && \
    useradd -r -u 1001 -g raguser raguser && \
    chown -R raguser:raguser /app

# Switch to non-root user
USER raguser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"] 