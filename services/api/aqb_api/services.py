from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aqb_eval.adapters import AgentAdapter, AqbHttpAdapter, DemoAdapter, OpenAICompatibleAdapter
from aqb_eval.judge import OpenAIResponsesJudge
from aqb_eval.metrics import evaluate_trial
from aqb_eval.models import (
    AgentExecution,
    AgentProfile,
    BenchmarkSuite,
    MetricObservation,
    RunCreate,
    RunResult,
    TrialResult,
)
from aqb_eval.runner import execute_run
from aqb_eval.scoring import aggregate_run
from aqb_eval.stats import mean, paired_bootstrap_delta
from aqb_eval.suites import load_suite
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .db import SessionLocal
from .security import decrypt_secret
from .settings import Settings, get_settings
from .tables import AgentRecord, CredentialRecord, MetricRecord, RunRecord, SuiteRecord, TrialRecord

ROOT = Path(__file__).resolve().parents[3]
STARTER_SUITE = ROOT / "benchmark-packs" / "starter" / "core.yaml"


def seed_defaults(db: Session) -> None:
    for agent_id, name, strength in (
        ("demo-strong", "Atlas / deterministic strong", "strong"),
        ("demo-brittle", "Flicker / deterministic brittle", "brittle"),
    ):
        if db.get(AgentRecord, agent_id) is None:
            db.add(
                AgentRecord(
                    id=agent_id,
                    name=name,
                    adapter_type="demo",
                    config={"strength": strength},
                )
            )
    suite = load_suite(STARTER_SUITE)
    suite_id = "suite-starter-core"
    if db.get(SuiteRecord, suite_id) is None:
        payload = suite.model_dump(mode="json")
        db.add(
            SuiteRecord(
                id=suite_id,
                suite_key=suite.id,
                name=suite.name,
                version=suite.version,
                payload=payload,
                configuration_hash=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            )
        )
    db.commit()


def agent_profile(record: AgentRecord) -> AgentProfile:
    return AgentProfile.model_validate(
        {
            "id": record.id,
            "name": record.name,
            "adapter_type": record.adapter_type,
            "endpoint": record.endpoint,
            "model": record.model_name,
            "credential_ref": record.credential_ref,
            "config": record.config,
            "version": record.version,
        }
    )


def build_adapter(record: AgentRecord, db: Session, settings: Settings) -> AgentAdapter:
    secret = None
    if record.credential_ref:
        credential = db.get(CredentialRecord, record.credential_ref)
        if credential:
            secret = decrypt_secret(credential.encrypted_value, settings.encryption_key)
    if record.adapter_type == "demo":
        return DemoAdapter(record.config.get("strength", "strong"))
    if not record.endpoint:
        raise ValueError("live agent endpoint is missing")
    if record.adapter_type == "aqb_http":
        headers = {"Authorization": "Bearer " + secret} if secret else {}
        return AqbHttpAdapter(record.endpoint, headers=headers, allowlist=settings.allowlist)
    if record.adapter_type == "openai_compatible":
        if not record.model_name:
            raise ValueError("OpenAI-compatible agent requires a model")
        return OpenAICompatibleAdapter(
            record.endpoint,
            record.model_name,
            api_key=secret,
            allowlist=settings.allowlist,
        )
    raise ValueError("unsupported adapter type")


def persist_run_result(db: Session, run_record: RunRecord, result: RunResult) -> None:
    run_record.status = result.status
    run_record.payload = result.model_dump(mode="json")
    run_record.configuration_hash = result.configuration_hash
    run_record.completed_at = result.completed_at
    db.execute(delete(MetricRecord).where(MetricRecord.run_id == run_record.id))
    db.execute(delete(TrialRecord).where(TrialRecord.run_id == run_record.id))
    for trial in result.trials:
        db.add(
            TrialRecord(
                id=trial.trial_id,
                run_id=run_record.id,
                case_id=trial.case_id,
                variant_id=trial.variant_id,
                repetition=trial.repetition,
                status=trial.execution.status,
                output=trial.execution.output,
                final_state=trial.execution.final_state,
                events=[event.model_dump(mode="json") for event in trial.execution.events],
                usage=trial.execution.usage.model_dump(mode="json"),
            )
        )
        for metric in trial.metrics:
            db.add(
                MetricRecord(
                    id=str(uuid.uuid4()),
                    run_id=run_record.id,
                    trial_id=trial.trial_id,
                    metric_key=metric.metric_key,
                    category=metric.category.value,
                    status=metric.status,
                    raw_value=metric.raw_value,
                    normalized_score=metric.normalized_score,
                    payload=metric.model_dump(mode="json"),
                    critical=metric.critical,
                )
            )
    db.commit()


def ingest_trace_bundle(db: Session, bundle: dict[str, Any]) -> RunResult:
    manifest = bundle["manifest"]
    suite_ref = manifest.get("suite") or {}
    suite_record = None
    for identifier in (suite_ref.get("database_id"), suite_ref.get("id")):
        if identifier:
            suite_record = db.get(SuiteRecord, str(identifier))
            if suite_record:
                break
    if suite_record is None and suite_ref.get("id"):
        suite_record = db.query(SuiteRecord).filter_by(suite_key=str(suite_ref["id"])).first()
    if suite_record is None:
        suite_record = db.get(SuiteRecord, "suite-starter-core")
    if suite_record is None:
        raise ValueError("trace suite is not installed and no starter suite is available")
    suite = BenchmarkSuite.model_validate(suite_record.payload)
    cases = {case.id: case for case in suite.cases}

    run_id = str(uuid.uuid4())
    agent_payload = manifest.get("agent") or {}
    agent_id = "trace-" + str(uuid.uuid4())
    agent_record = AgentRecord(
        id=agent_id,
        name=str(agent_payload.get("name") or "Imported trace"),
        adapter_type="trace_upload",
        config={"source_agent": agent_payload, "immutable": True},
    )
    db.add(agent_record)
    db.flush()
    profile = agent_profile(agent_record)
    digest = str(manifest.get("configuration_hash") or hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest())
    run_record = RunRecord(
        id=run_id,
        agent_id=agent_id,
        suite_id=suite_record.id,
        status="running",
        configuration_hash=digest,
        payload={"run_id": run_id, "status": "running"},
    )
    db.add(run_record)
    db.flush()
    trials: list[TrialResult] = []
    for index, item in enumerate(bundle["trials"]):
        case_id = str(item.get("case_id", ""))
        if case_id not in cases and not item.get("metrics"):
            raise ValueError(f"trace trial {index} references an unknown case without metric observations")
        execution_payload = item.get("execution") or {
            "status": item.get("status"),
            "output": item.get("output", ""),
            "final_state": item.get("final_state", {}),
            "events": item.get("events", []),
            "usage": item.get("usage", {}),
            "metadata": {"raw_source": item.get("raw_source")},
        }
        execution = AgentExecution.model_validate(execution_payload)
        metrics = [MetricObservation.model_validate(metric) for metric in item.get("metrics", [])]
        if not metrics:
            metrics = evaluate_trial(cases[case_id], execution)
        trials.append(
            TrialResult(
                trial_id=str(item.get("trial_id") or uuid.uuid4()),
                case_id=case_id,
                variant_id=item.get("variant_id"),
                repetition=int(item.get("repetition", 1)),
                execution=execution,
                metrics=metrics,
            )
        )
    result = RunResult(
        run_id=run_id,
        agent=profile,
        suite=suite,
        status="completed",
        configuration_hash=digest,
        trials=trials,
        summary=aggregate_run(trials, suite),
        completed_at=datetime.now(timezone.utc),
        metadata={"source": "trace_upload", "original_manifest": manifest},
    )
    persist_run_result(db, run_record, result)
    return result


async def run_in_background(run_id: str, request: RunCreate) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        run_record = db.get(RunRecord, run_id)
        if not run_record:
            return
        agent_record = db.get(AgentRecord, run_record.agent_id)
        suite_record = db.get(SuiteRecord, run_record.suite_id)
        if not agent_record or not suite_record:
            run_record.status = "failed"
            run_record.payload = {"error": "agent or suite no longer exists"}
            db.commit()
            return
        run_record.status = "running"
        db.commit()
        profile = agent_profile(agent_record)
        suite = BenchmarkSuite.model_validate(suite_record.payload)
        adapter = build_adapter(agent_record, db, settings)
        judge = OpenAIResponsesJudge() if request.enable_model_judge else None
        result = await execute_run(
            run_id=run_id,
            agent=profile,
            adapter=adapter,
            suite=suite,
            repetitions=request.repetitions,
            seed=request.seed,
            judge=judge,
        )
        persist_run_result(db, run_record, result)


def compare_runs(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_categories = {item["category"]: item for item in baseline.get("summary", {}).get("categories", [])}
    candidate_categories = {item["category"]: item for item in candidate.get("summary", {}).get("categories", [])}
    baseline_trials = {
        (trial.get("case_id"), trial.get("variant_id"), trial.get("repetition")): trial
        for trial in baseline.get("trials", [])
    }
    candidate_trials = {
        (trial.get("case_id"), trial.get("variant_id"), trial.get("repetition")): trial
        for trial in candidate.get("trials", [])
    }
    aligned_keys = sorted(set(baseline_trials) & set(candidate_trials), key=repr)

    def trial_category_score(trial: dict[str, Any], category: str) -> float | None:
        values = [
            float(metric["normalized_score"])
            for metric in trial.get("metrics", [])
            if metric.get("category") == category
            and metric.get("status") == "measured"
            and metric.get("normalized_score") is not None
        ]
        return mean(values) if values else None

    def paired_category(category: str) -> tuple[list[float], list[float]]:
        left: list[float] = []
        right: list[float] = []
        for key in aligned_keys:
            baseline_score = trial_category_score(baseline_trials[key], category)
            candidate_score = trial_category_score(candidate_trials[key], category)
            if baseline_score is not None and candidate_score is not None:
                left.append(baseline_score)
                right.append(candidate_score)
        return left, right

    deltas = []
    for category in sorted(set(baseline_categories) & set(candidate_categories)):
        left = float(baseline_categories[category]["score"])
        right = float(candidate_categories[category]["score"])
        paired_left, paired_right = paired_category(category)
        interval_payload = None
        demonstrated = None
        if paired_left:
            _, interval = paired_bootstrap_delta(paired_left, paired_right)
            interval_payload = interval.model_dump(mode="json")
            demonstrated = interval.low > 0 or interval.high < 0
        deltas.append(
            {
                "category": category,
                "baseline": left,
                "candidate": right,
                "delta": round(right - left, 2),
                "interval": interval_payload,
                "demonstrated": demonstrated,
                "paired_observations": len(paired_left),
            }
        )
    left_index = baseline.get("summary", {}).get("quality_index")
    right_index = candidate.get("summary", {}).get("quality_index")
    quality_delta = round(float(right_index) - float(left_index), 2) if left_index is not None and right_index is not None else None
    quality_pairs_left: list[float] = []
    quality_pairs_right: list[float] = []
    for key in aligned_keys:
        left_values = [
            float(metric["normalized_score"])
            for metric in baseline_trials[key].get("metrics", [])
            if metric.get("status") == "measured" and metric.get("normalized_score") is not None
        ]
        right_values = [
            float(metric["normalized_score"])
            for metric in candidate_trials[key].get("metrics", [])
            if metric.get("status") == "measured" and metric.get("normalized_score") is not None
        ]
        if left_values and right_values:
            quality_pairs_left.append(mean(left_values))
            quality_pairs_right.append(mean(right_values))
    quality_interval = None
    demonstrated = None
    if quality_pairs_left:
        _, interval = paired_bootstrap_delta(quality_pairs_left, quality_pairs_right)
        quality_interval = interval.model_dump(mode="json")
        demonstrated = interval.low > 0 or interval.high < 0
    if quality_delta is None:
        verdict = "insufficient evidence"
    elif demonstrated is False:
        verdict = "no demonstrated difference"
    elif quality_delta > 0:
        verdict = "candidate leads"
    else:
        verdict = "baseline leads"
    return {
        "category_deltas": deltas,
        "quality_index_delta": quality_delta,
        "quality_interval": quality_interval,
        "demonstrated": demonstrated,
        "paired_observations": len(quality_pairs_left),
        "verdict": verdict,
    }
