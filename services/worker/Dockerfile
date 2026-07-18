FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/eval-core:/app/services/api:/app/services/worker

WORKDIR /app
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2 uv==0.11.28
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev
COPY packages ./packages
COPY services ./services
COPY benchmark-packs ./benchmark-packs
RUN mkdir -p /data/artifacts

CMD ["uv", "run", "celery", "-A", "aqb_worker.celery_app:celery_app", "worker", "--loglevel=INFO", "--concurrency=2"]
