# SPEC §23.1-23.5: Locus Sidecar Dockerfile (FastAPI ML/NLP/computation container)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8420

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY sidecar/ ./sidecar/
COPY data/ ./data/

EXPOSE 8420

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8420/health || exit 1

CMD ["python", "-m", "uvicorn", "sidecar.service:app", "--host", "127.0.0.1", "--port", "8420"]
