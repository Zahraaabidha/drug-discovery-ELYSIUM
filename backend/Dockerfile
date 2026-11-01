FROM python:3.11-slim

# System deps required for RDKit and ML libs
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    git \
    libxrender1 \
    libxext6 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV HF_HOME=/app/.hf_cache
ENV TRANSFORMERS_CACHE=/app/.hf_cache

# ---------------------------
# Install base dependencies
# ---------------------------
COPY backend/requirements-base.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements-base.txt

# ---------------------------
# Install ML dependencies
# ---------------------------
COPY backend/requirements-ml.txt .
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    --default-timeout=300 \
    -r requirements-ml.txt

# ---------------------------
# Copy application code
# ---------------------------
COPY backend/app ./app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
