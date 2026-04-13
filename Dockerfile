# ─── Build stage ─────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Runtime stage ───────────────────────────────────────────────────
FROM python:3.13-slim

LABEL maintainer="d4kw1n"
LABEL description="LifeBot - Personal Finance + Fitness Telegram Bot"

# System deps for matplotlib font rendering + tini for signal handling
RUN apt-get update && \
    apt-get install -y --no-install-recommends fonts-dejavu-core tini && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

# Create data & matplotlib config directories
RUN useradd -m -r botuser && \
    mkdir -p /app/data /app/.config/matplotlib && \
    chown -R botuser:botuser /app/data /app/.config

ENV MPLCONFIGDIR=/app/.config/matplotlib

USER botuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os; exit(0)"

ENTRYPOINT ["tini", "--"]
CMD ["python", "run.py"]
