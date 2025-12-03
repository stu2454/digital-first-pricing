# ───────────────────────────────────────────────
# Base image
# ───────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ───────────────────────────────────────────────
# Install system dependencies
# ───────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ───────────────────────────────────────────────
# Copy application code (App 2)
# ───────────────────────────────────────────────
COPY . /app

# ───────────────────────────────────────────────
# Copy shared module (from root directory)
# Render automatically includes the ENTIRE repo
# ───────────────────────────────────────────────
COPY ../../shared /app/shared

# ───────────────────────────────────────────────
# Install Python dependencies
# ───────────────────────────────────────────────
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir -r /app/shared/requirements.txt

# ───────────────────────────────────────────────
# Streamlit config
# ───────────────────────────────────────────────
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    PYTHONPATH="/app:/app/shared"

EXPOSE 8501

# ───────────────────────────────────────────────
# Run the app
# ───────────────────────────────────────────────
CMD ["streamlit", "run", "app.py"]
