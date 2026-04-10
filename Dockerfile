# ─── Build stage ─────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Runtime stage ───────────────────────────────────────────────────
FROM python:3.13-slim

LABEL maintainer="d4kw1n"
LABEL description="FinBot - Personal Finance Telegram Bot"

# System deps for matplotlib font rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Health indicator via process
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os; exit(0)"

CMD ["python", "run.py"]
