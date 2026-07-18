FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/eval-core:/app/services/api:/app/services/worker

WORKDIR /app
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2 uv==0.11.28
COPY pyproject.toml uv.lock* alembic.ini ./
RUN uv sync --no-dev
COPY packages ./packages
COPY services ./services
COPY benchmark-packs ./benchmark-packs
RUN mkdir -p /data/artifacts
RUN chmod 0755 services/api/entrypoint.sh

EXPOSE 8000
CMD ["services/api/entrypoint.sh"]
