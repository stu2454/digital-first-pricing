# ─────────────────────────────────────────────
# 1. Base image
# ─────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system packages (needed for python-docx, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────
# 2. Copy shared + app code
# ─────────────────────────────────────────────
COPY shared /app/shared
COPY apps/02-papl-comparison /app

# ─────────────────────────────────────────────
# 3. Install all requirements
# ─────────────────────────────────────────────
# global requirements in project root
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# app-specific requirements
RUN if [ -f "/app/requirements.txt" ]; then pip install -r /app/requirements.txt; fi

# ─────────────────────────────────────────────
# 4. Expose and run app
# ─────────────────────────────────────────────
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
