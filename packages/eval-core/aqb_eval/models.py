from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Category(str, Enum):
    OUTCOME = "outcome"
    ADHERENCE = "adherence"
    TOOLS = "tools"
    CONTEXT = "context"
    RELIABILITY = "reliability"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    FAIRNESS = "fairness"
    EVALUATOR_QUALITY = "evaluator_quality"


class EvaluatorIdentity(BaseModel):
    kind: Literal["deterministic", "declarative", "model", "human"]
    name: str
    version: str = "0.1.0"
    model: str | None = None
    prompt_version: str | None = None
    calibrated: bool = False


class ConfidenceInterval(BaseModel):
    low: float
    high: float
    level: float = 0.95


class MetricObservation(BaseModel):
    protocol_version: Literal["aqb.metric.v1"] = "aqb.metric.v1"
    metric_key: str
    category: Category
    definition: str
    status: Literal["measured", "not_applicable", "insufficient_evidence", "error"]
    raw_value: Any = None
    unit: str | None = None
    normalized_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    interval: ConfidenceInterval | None = None
    evaluator: EvaluatorIdentity
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    critical: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class Message(BaseModel):
    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class TraceEvent(BaseModel):
    event_id: str
    parent_event_id: str | None = None
    kind: Literal["agent", "model", "tool", "retrieval", "memory", "guardrail", "error"]
    name: str = ""
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    input: Any = None
    output: Any = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Usage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)


class AgentExecution(BaseModel):
    status: Literal["succeeded", "failed", "refused", "timed_out", "errored"]
    output: str = ""
    final_state: dict[str, Any] = Field(default_factory=dict)
    events: list[TraceEvent] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentProfile(BaseModel):
    id: str
    name: str
    adapter_type: Literal["trace_upload", "openai_compatible", "aqb_http", "demo"]
    endpoint: HttpUrl | None = None
    model: str | None = None
    credential_ref: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    version: str = "1"


class BenchmarkCase(BaseModel):
    id: str
    category: str
    input: dict[str, Any]
    expected: dict[str, Any] = Field(default_factory=dict)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    context: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    evaluators: list[dict[str, Any]] = Field(default_factory=list)
    limits: dict[str, Any] = Field(default_factory=dict)
    repetitions: int = Field(default=1, ge=1, le=10)
    perturbations: list[dict[str, Any]] = Field(default_factory=list)
    ablations: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ScoreProfile(BaseModel):
    weights: dict[Category, float] = Field(
        default_factory=lambda: {
            Category.OUTCOME: 0.30,
            Category.ADHERENCE: 0.15,
            Category.TOOLS: 0.10,
            Category.CONTEXT: 0.10,
            Category.RELIABILITY: 0.15,
            Category.SAFETY: 0.15,
            Category.EFFICIENCY: 0.05,
        }
    )
    minimum_coverage: float = Field(default=0.8, ge=0, le=1)
    required_categories: list[Category] = Field(
        default_factory=lambda: [Category.OUTCOME, Category.SAFETY]
    )

    @model_validator(mode="after")
    def weights_must_be_positive(self) -> ScoreProfile:
        if sum(self.weights.values()) <= 0:
            raise ValueError("profile weights must have a positive total")
        return self


class BenchmarkSuite(BaseModel):
    protocol_version: Literal["aqb.suite.v1"] = "aqb.suite.v1"
    id: str
    name: str
    version: str
    description: str = ""
    license: str = "MIT"
    provenance: dict[str, Any] = Field(default_factory=dict)
    profile: ScoreProfile = Field(default_factory=ScoreProfile)
    readiness_gates: list[dict[str, Any]] = Field(default_factory=list)
    defaults: dict[str, Any] = Field(default_factory=dict)
    cases: list[BenchmarkCase]


class TrialResult(BaseModel):
    trial_id: str
    case_id: str
    variant_id: str | None = None
    repetition: int = 1
    execution: AgentExecution
    metrics: list[MetricObservation] = Field(default_factory=list)


class CategoryScore(BaseModel):
    category: Category
    score: float
    weight: float
    observations: int
    interval: ConfidenceInterval | None = None


class RunSummary(BaseModel):
    quality_index: float | None
    coverage: float = Field(ge=0, le=1)
    readiness: Literal["pass", "fail", "insufficient_evidence"]
    readiness_reasons: list[str]
    categories: list[CategoryScore]
    task_success_rate: float
    pass_at_k: dict[str, float]
    pass_power_k: dict[str, float]
    latency_p50_ms: float
    latency_p95_ms: float
    total_cost_usd: float
    cost_per_success_usd: float | None
    critical_findings: list[dict[str, Any]]


class RunResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    protocol_version: Literal["aqb.trace.v1"] = "aqb.trace.v1"
    run_id: str
    agent: AgentProfile
    suite: BenchmarkSuite
    status: Literal["queued", "running", "completed", "failed", "canceled"] = "queued"
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    configuration_hash: str
    trials: list[TrialResult] = Field(default_factory=list)
    summary: RunSummary | None = None
    judge_status: Literal["disabled", "configured", "unavailable", "used"] = "disabled"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunCreate(BaseModel):
    agent_id: str
    suite_id: str
    repetitions: int = Field(default=3, ge=1, le=10)
    enable_model_judge: bool = False
    seed: int = 42
