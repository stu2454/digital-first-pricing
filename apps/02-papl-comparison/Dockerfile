FROM python:3.11-slim

# Prevent Python from writing bytecode
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy shared modules (from repo root)
COPY shared /app/shared

# Copy App 2 code (from repo root)
COPY apps/02-papl-comparison /app

COPY apps/02-papl-comparison/requirements.txt /app/requirements.txt


# Install dependencies for App 2
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
