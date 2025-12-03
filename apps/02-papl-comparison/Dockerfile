# ───────────────────────────────────────────────
# Base image
# ───────────────────────────────────────────────
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ───────────────────────────────────────────────
# System Dependencies
# ───────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ───────────────────────────────────────────────
# Set working directory (NOTE: Render expects this)
# ───────────────────────────────────────────────
WORKDIR /app

# Copy APP 2 files
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

# Copy shared library
COPY ../../shared /app/shared

# ───────────────────────────────────────────────
# Install Python dependencies
# ───────────────────────────────────────────────
RUN pip install --no-cache-dir -r /app/requirements.txt

# ───────────────────────────────────────────────
# Streamlit environment (Render requirement)
# ───────────────────────────────────────────────
ENV STREAMLIT_SERVER_PORT=10000 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PYTHONPATH="/app:/app/shared"

# ───────────────────────────────────────────────
# Expose Render port
# ───────────────────────────────────────────────
EXPOSE 10000

# ───────────────────────────────────────────────
# Run Streamlit app
# ───────────────────────────────────────────────
CMD ["streamlit", "run", "/app/app.py"]
