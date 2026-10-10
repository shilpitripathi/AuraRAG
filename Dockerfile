# AuraRAG Backend Production Dockerfile
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies including ffmpeg (mandatory for Whisper STT)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY app/ ./app/

# Create persistent storage directories
RUN mkdir -p /app/data/documents /app/data/voice /app/chroma_db

# Set default environment variables
ENV PORT=8000 \
    DEPLOYMENT_ENV=production \
    ENABLE_LOCAL_FILE_ACCESS=false \
    CHROMA_PERSIST_DIR=/app/chroma_db

EXPOSE 8000

# Run FastAPI backend with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
