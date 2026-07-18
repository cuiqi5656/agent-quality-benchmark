from __future__ import annotations

from aqb_api.settings import get_settings
from celery import Celery

settings = get_settings()
celery_app = Celery("aqb", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    timezone="UTC",
)
celery_app.autodiscover_tasks(["aqb_worker"])
