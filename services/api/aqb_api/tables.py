from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentRecord(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    adapter_type: Mapped[str] = mapped_column(String(40), index=True)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    credential_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(40), default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CredentialRecord(Base):
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    encrypted_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SuiteRecord(Base):
    __tablename__ = "suites"
    __table_args__ = (UniqueConstraint("suite_key", "version", name="uq_suite_version"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    suite_key: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(240))
    version: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    configuration_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    suite_id: Mapped[str] = mapped_column(ForeignKey("suites.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    configuration_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrialRecord(Base):
    __tablename__ = "trials"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[str] = mapped_column(String(200), index=True)
    variant_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    repetition: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    output: Mapped[str] = mapped_column(Text)
    final_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MetricRecord(Base):
    __tablename__ = "metric_observations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    trial_id: Mapped[str | None] = mapped_column(ForeignKey("trials.id", ondelete="CASCADE"), nullable=True, index=True)
    metric_key: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40))
    raw_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    normalized_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    critical: Mapped[bool] = mapped_column(Boolean, default=False)


class HumanReviewRecord(Base):
    __tablename__ = "human_reviews"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    trial_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metric_key: Mapped[str] = mapped_column(String(160))
    reviewer: Mapped[str] = mapped_column(String(160), default="local-reviewer")
    label: Mapped[str] = mapped_column(String(80))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class JudgeVersionRecord(Base):
    __tablename__ = "judge_versions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    provider: Mapped[str] = mapped_column(String(80))
    model_name: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(80))
    calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    calibration_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ArtifactRecord(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(80))
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    operation: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
