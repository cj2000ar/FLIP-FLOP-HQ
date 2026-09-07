FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY hp_api.py .
COPY hp_infra.py .
COPY private_read_api.py .
COPY logging_config.py .
COPY monitoring.py .
COPY backup.py .
COPY ninjatrader_bridge.py .
COPY RED_DRAGON/ ./RED_DRAGON/

# Create directories
RUN mkdir -p /app/databases /app/logs

# Create non-root user
RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "hp_api.py"]
