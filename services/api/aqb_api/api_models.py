from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    adapter_type: Literal["openai_compatible", "aqb_http", "demo"]
    endpoint: HttpUrl | None = None
    model: str | None = None
    secret: str | None = Field(default=None, repr=False)
    config: dict[str, Any] = Field(default_factory=dict)


class ReviewCreate(BaseModel):
    run_id: str
    trial_id: str | None = None
    metric_key: str
    label: str
    score: float | None = Field(default=None, ge=0, le=100)
    notes: str = ""
    reviewer: str = "local-reviewer"


class ComparisonResponse(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    category_deltas: list[dict[str, Any]]
    quality_index_delta: float | None
    verdict: str
