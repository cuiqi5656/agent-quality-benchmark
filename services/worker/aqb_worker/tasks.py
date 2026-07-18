from __future__ import annotations

import asyncio
from typing import Any

from aqb_api.services import run_in_background
from aqb_eval.models import RunCreate

from .celery_app import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="aqb.execute_run", autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3
)
def execute_run_task(run_id: str, request: dict[str, Any]) -> None:
    asyncio.run(run_in_background(run_id, RunCreate.model_validate(request)))
