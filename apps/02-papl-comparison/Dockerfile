# ---------------------------------------------------------
# 1. Base Image
# ---------------------------------------------------------
FROM python:3.11-slim

# Prevent Python writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------------------------------------------------------
# 2. System Dependencies
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 3. Create working directory
# NOTE: Render resolves this relative to repository root.
# ---------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------
# 4. Copy app folder into container
# ---------------------------------------------------------
COPY apps/02-papl-comparison /app

# ---------------------------------------------------------
# 5. Copy shared modules
# (Render's build context is repo root → so this path works)
# ---------------------------------------------------------
COPY shared /app/shared

# ---------------------------------------------------------
# 5.1. install LibreOffice for PDF to DOCX conversion
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 6. Install Python Dependencies
# ---------------------------------------------------------

# Upgrade pip first
RUN pip install --upgrade pip

# Install app dependencies
RUN pip install -r /app/requirements.txt

# Install shared dependencies
RUN pip install -r /app/shared/requirements.txt

# ---------------------------------------------------------
# 7. Streamlit environment config
# ---------------------------------------------------------
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0



# ---------------------------------------------------------
# 8. Start Application
# ---------------------------------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
