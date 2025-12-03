FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared modules from project root
COPY shared /app/shared

# Copy app files from the app directory
COPY apps/02-papl-comparison/requirements.txt /app/requirements.txt
COPY apps/02-papl-comparison/app.py /app/app.py

# Install Python dependencies (shared first, then app-specific)
RUN pip install --no-cache-dir -r /app/shared/requirements.txt && \
    pip install --no-cache-dir -r /app/requirements.txt

# Create non-root user
RUN useradd -m -u 1000 streamlit && chown -R streamlit:streamlit /app
USER streamlit

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run app
CMD ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.maxUploadSize=500"]