# LegalAI Hub Enterprise - Railway Deployment
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production

# Install system dependencies for enterprise features
RUN apt-get update && apt-get install -y \
    # OCR and document processing
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    # Graphics and image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Database client for PostgreSQL
    postgresql-client \
    # Health checks and utilities
    curl \
    # Security and performance tools
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt .
COPY requirements-railway.txt .

# Install Python dependencies with better error handling
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-railway.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/documents /app/logs && \
    chmod -R 755 /app/data /app/documents /app/logs

# Make startup script executable
RUN chmod +x start_railway.sh

# Create a non-root user for security
RUN groupadd -r legalai && useradd -r -g legalai -m -s /bin/bash legalai && \
    chown -R legalai:legalai /app

# Switch to non-root user
USER legalai

# Expose port (Railway will set PORT environment variable)
EXPOSE 8501

# Health check for Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail http://localhost:${PORT:-8501}/_stcore/health || exit 1

# Set labels for metadata
LABEL maintainer="LegalAI Hub Enterprise" \
      version="1.0" \
      description="Multi-tenant Legal AI Platform for Australian Family Law" \
      deployment="railway" \
      jurisdiction="australia"

# Run the application using startup script
CMD ["./start_railway.sh"]

