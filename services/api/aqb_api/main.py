from __future__ import annotations

import asyncio
import csv
import hashlib
import html
import io
import json
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from aqb_eval.adapters import UnsafeEndpointError, validate_stable_endpoint
from aqb_eval.models import BenchmarkSuite, RunCreate
from aqb_eval.otel import map_otel_spans
from aqb_eval.stats import cohen_kappa
from aqb_eval.uploads import UnsafeUploadError, parse_trace_upload, validate_trace_bundle
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from .api_models import AgentCreate, ReviewCreate
from .db import Base, engine, get_db
from .security import SecretConfigurationError, encrypt_secret, safe_artifact_path, sha256_bytes
from .services import compare_runs, ingest_trace_bundle, run_in_background, seed_defaults
from .settings import get_settings
from .tables import (
    AgentRecord,
    ArtifactRecord,
    CredentialRecord,
    HumanReviewRecord,
    IdempotencyRecord,
    MetricRecord,
    RunRecord,
    SuiteRecord,
    TrialRecord,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        seed_defaults(db)
    yield


app = FastAPI(
    title="Agent Quality Benchmark API",
    version="0.1.0",
    description="Evidence-first evaluation, comparison, and reporting for AI agents.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


def _agent_response(record: AgentRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "adapter_type": record.adapter_type,
        "endpoint": record.endpoint,
        "model": record.model_name,
        "has_credential": bool(record.credential_ref),
        "config": record.config,
        "version": record.version,
        "created_at": record.created_at,
    }


def _suite_response(record: SuiteRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "suite_key": record.suite_key,
        "name": record.name,
        "version": record.version,
        "case_count": len(record.payload.get("cases", [])),
        "configuration_hash": record.configuration_hash,
        "provenance": record.payload.get("provenance", {}),
        "created_at": record.created_at,
    }


def _run_response(record: RunRecord, *, detailed: bool = True) -> dict[str, Any]:
    payload = dict(record.payload or {})
    base = {
        "run_id": record.id,
        "agent_id": record.agent_id,
        "suite_id": record.suite_id,
        "status": record.status,
        "configuration_hash": record.configuration_hash,
        "created_at": record.created_at,
        "completed_at": record.completed_at,
    }
    if detailed:
        return {**payload, **base}
    return {
        **base,
        "summary": payload.get("summary"),
        "agent": payload.get("agent"),
        "suite": {key: value for key, value in (payload.get("suite") or {}).items() if key != "cases"},
    }


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "judge": {
            "configured": bool(os.getenv("OPENAI_API_KEY")),
            "model": os.getenv("OPENAI_JUDGE_MODEL", "gpt-5.6-terra"),
            "status": "configured" if os.getenv("OPENAI_API_KEY") else "final setup TODO",
        },
        "execution_mode": settings.execution_mode,
    }


@app.get("/api/v1/agents")
def list_agents(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_agent_response(record) for record in db.scalars(select(AgentRecord).order_by(AgentRecord.created_at)).all()]


@app.post("/api/v1/agents", status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.adapter_type != "demo" and not payload.endpoint:
        raise HTTPException(status_code=422, detail="live agents require an endpoint")
    if payload.adapter_type == "openai_compatible" and not payload.model:
        raise HTTPException(status_code=422, detail="OpenAI-compatible agents require a model")
    credential_ref = None
    if payload.secret:
        try:
            encrypted = encrypt_secret(payload.secret, settings.encryption_key)
        except SecretConfigurationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        credential_ref = str(uuid.uuid4())
        db.add(CredentialRecord(id=credential_ref, name=payload.name + " credential", encrypted_value=encrypted))
    record = AgentRecord(
        id=str(uuid.uuid4()),
        name=payload.name,
        adapter_type=payload.adapter_type,
        endpoint=str(payload.endpoint) if payload.endpoint else None,
        model_name=payload.model,
        credential_ref=credential_ref,
        config=payload.config,
    )
    db.add(record)
    db.commit()
    return _agent_response(record)


@app.post("/api/v1/agents/{agent_id}/test")
async def test_agent(agent_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    record = db.get(AgentRecord, agent_id)
    if not record:
        raise HTTPException(status_code=404, detail="agent not found")
    if record.adapter_type == "demo":
        return {"status": "ok", "message": "deterministic demo adapter is ready"}
    try:
        await validate_stable_endpoint(str(record.endpoint), settings.allowlist)
    except UnsafeEndpointError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "ok", "message": "endpoint passed scheme, DNS, and allowlist validation"}


@app.get("/api/v1/suites")
def list_suites(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_suite_response(record) for record in db.scalars(select(SuiteRecord).order_by(SuiteRecord.created_at)).all()]


@app.post("/api/v1/suites", status_code=status.HTTP_201_CREATED)
def create_suite(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        suite = BenchmarkSuite.model_validate(payload)
    except Exception as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    normalized = suite.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    record = SuiteRecord(
        id=str(uuid.uuid4()),
        suite_key=suite.id,
        name=suite.name,
        version=suite.version,
        payload=normalized,
        configuration_hash=digest,
    )
    db.add(record)
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="this suite version already exists") from error
    return _suite_response(record)


@app.post("/api/v1/suites/import-yaml", status_code=status.HTTP_201_CREATED)
async def import_suite_yaml(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, Any]:
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="suite file exceeds upload limit")
    try:
        payload = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise HTTPException(status_code=422, detail="invalid YAML") from error
    return create_suite(payload, db)


@app.get("/api/v1/runs")
def list_runs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    records = db.scalars(select(RunRecord).order_by(RunRecord.created_at.desc()).limit(100)).all()
    return [_run_response(record, detailed=False) for record in records]


@app.post("/api/v1/runs", status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if idempotency_key:
        existing = db.get(IdempotencyRecord, idempotency_key)
        if existing:
            record = db.get(RunRecord, existing.resource_id)
            if record:
                return _run_response(record, detailed=False)
    if not db.get(AgentRecord, payload.agent_id):
        raise HTTPException(status_code=404, detail="agent not found")
    if not db.get(SuiteRecord, payload.suite_id):
        raise HTTPException(status_code=404, detail="suite not found")
    run_id = str(uuid.uuid4())
    digest = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    record = RunRecord(
        id=run_id,
        agent_id=payload.agent_id,
        suite_id=payload.suite_id,
        status="queued",
        configuration_hash=digest,
        payload={"run_id": run_id, "status": "queued"},
    )
    db.add(record)
    if idempotency_key:
        db.add(IdempotencyRecord(key=idempotency_key, operation="create_run", resource_id=run_id))
    db.commit()
    if settings.execution_mode == "celery":
        from aqb_worker.tasks import execute_run_task

        execute_run_task.delay(run_id, payload.model_dump(mode="json"))
    else:
        background_tasks.add_task(run_in_background, run_id, payload)
    return _run_response(record, detailed=False)


@app.get("/api/v1/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    record = db.get(RunRecord, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_response(record)


@app.get("/api/v1/runs/{run_id}/events")
async def stream_run(run_id: str) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        last_status = None
        while True:
            with next(get_db()) as db:
                record = db.get(RunRecord, run_id)
                if not record:
                    yield "event: error\ndata: {\"message\":\"run not found\"}\n\n"
                    return
                if record.status != last_status:
                    data = json.dumps({"run_id": run_id, "status": record.status})
                    yield f"event: status\ndata: {data}\n\n"
                    last_status = record.status
                if record.status in {"completed", "failed", "canceled"}:
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


@app.delete("/api/v1/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, db: Session = Depends(get_db)) -> None:
    record = db.get(RunRecord, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")
    artifacts = db.scalars(select(ArtifactRecord).where(ArtifactRecord.run_id == run_id)).all()
    for artifact in artifacts:
        path = Path(artifact.path)
        if path.is_file() and settings.storage_path.resolve() in path.resolve().parents:
            path.unlink()
    db.execute(delete(HumanReviewRecord).where(HumanReviewRecord.run_id == run_id))
    db.execute(delete(MetricRecord).where(MetricRecord.run_id == run_id))
    db.execute(delete(TrialRecord).where(TrialRecord.run_id == run_id))
    db.execute(delete(ArtifactRecord).where(ArtifactRecord.run_id == run_id))
    db.delete(record)
    db.commit()


@app.post("/api/v1/uploads/traces", status_code=status.HTTP_201_CREATED)
async def upload_trace(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, Any]:
    allowed_mime = {
        "application/json",
        "application/jsonl",
        "application/x-ndjson",
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
    }
    if file.content_type and file.content_type not in allowed_mime:
        raise HTTPException(status_code=415, detail="unsupported trace MIME type")
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        payload = parse_trace_upload(
            file.filename or "trace",
            content,
            max_upload_bytes=settings.max_upload_bytes,
            max_extracted_bytes=settings.max_extracted_bytes,
        )
        bundle = validate_trace_bundle(payload)
    except (UnsafeUploadError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    artifact_id = str(uuid.uuid4())
    target = safe_artifact_path(settings.storage_path, artifact_id, ".upload")
    target.write_bytes(content)
    db.add(
        ArtifactRecord(
            id=artifact_id,
            run_id=None,
            kind="trace_upload",
            path=str(target),
            sha256=sha256_bytes(content),
            size_bytes=len(content),
        )
    )
    try:
        result = ingest_trace_bundle(db, bundle)
        artifact = db.get(ArtifactRecord, artifact_id)
        if artifact:
            artifact.run_id = result.run_id
        db.commit()
    except ValueError as error:
        db.rollback()
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "artifact_id": artifact_id,
        "run_id": result.run_id,
        "protocol_version": bundle["protocol_version"],
        "trial_count": len(bundle["trials"]),
        "manifest": bundle["manifest"],
        "summary": result.summary.model_dump(mode="json") if result.summary else None,
    }


@app.post("/api/v1/uploads/otel", status_code=status.HTTP_201_CREATED)
def import_otel(payload: dict[str, Any]) -> dict[str, Any]:
    mapped = map_otel_spans(payload)
    return {"protocol_version": mapped["protocol_version"], "manifest": mapped["manifest"], "trials": mapped["trials"]}


@app.get("/api/v1/compare")
def compare(
    baseline_run_id: str = Query(...),
    candidate_run_id: str = Query(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    baseline = db.get(RunRecord, baseline_run_id)
    candidate = db.get(RunRecord, candidate_run_id)
    if not baseline or not candidate:
        raise HTTPException(status_code=404, detail="comparison run not found")
    result = compare_runs(baseline.payload, candidate.payload)
    return {"baseline_run_id": baseline_run_id, "candidate_run_id": candidate_run_id, **result}


@app.post("/api/v1/reviews", status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not db.get(RunRecord, payload.run_id):
        raise HTTPException(status_code=404, detail="run not found")
    record = HumanReviewRecord(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(record)
    db.commit()
    return {
        "id": record.id,
        "run_id": record.run_id,
        "trial_id": record.trial_id,
        "metric_key": record.metric_key,
        "label": record.label,
        "score": record.score,
        "notes": record.notes,
        "reviewer": record.reviewer,
        "created_at": record.created_at,
    }


@app.get("/api/v1/calibration")
def calibration(db: Session = Depends(get_db)) -> dict[str, Any]:
    reviews = db.scalars(select(HumanReviewRecord).order_by(HumanReviewRecord.created_at)).all()
    left: list[str] = []
    right: list[str] = []
    for review in reviews:
        if not review.trial_id:
            continue
        metric = db.scalar(
            select(MetricRecord).where(
                MetricRecord.trial_id == review.trial_id,
                MetricRecord.metric_key == review.metric_key,
            )
        )
        if metric and metric.normalized_score is not None:
            left.append("pass" if metric.normalized_score >= 70 else "fail")
            right.append(review.label)
    return {
        "review_count": len(reviews),
        "paired_labels": len(left),
        "cohen_kappa": cohen_kappa(left, right) if left else None,
        "calibrated": len(left) >= 20 and cohen_kappa(left, right) >= 0.6 if left else False,
        "note": "Model-derived metrics remain marked uncalibrated until reviewed labels meet the configured threshold.",
    }


@app.get("/api/v1/reports/{run_id}")
def report(
    run_id: str,
    format: str = Query("html", pattern="^(html|json|csv)$"),
    db: Session = Depends(get_db),
) -> Response:
    record = db.get(RunRecord, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")
    payload = _run_response(record)
    if format == "json":
        return JSONResponse(jsonable_encoder(payload))
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["trial_id", "case_id", "repetition", "category", "metric", "status", "raw_value", "normalized_score", "critical"])
        for trial in payload.get("trials", []):
            for metric in trial.get("metrics", []):
                writer.writerow(
                    [
                        trial.get("trial_id"),
                        trial.get("case_id"),
                        trial.get("repetition"),
                        metric.get("category"),
                        metric.get("metric_key"),
                        metric.get("status"),
                        json.dumps(metric.get("raw_value")),
                        metric.get("normalized_score"),
                        metric.get("critical"),
                    ]
                )
        return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="aqb-{run_id}.csv"'})
    summary = payload.get("summary") or {}
    category_rows = "".join(
        f"<tr><td>{html.escape(item['category'])}</td><td>{item['score']:.1f}</td><td>{item['observations']}</td></tr>"
        for item in summary.get("categories", [])
    )
    page = f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>AQB report {html.escape(run_id)}</title>
    <style>body{{font:15px system-ui;max-width:960px;margin:48px auto;color:#14151a}}h1{{font-size:32px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.card{{border:1px solid #ddd;border-radius:14px;padding:18px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}@media print{{body{{margin:16mm}}}}</style></head>
    <body><p>Agent Quality Benchmark · evidence report</p><h1>{html.escape(str((payload.get('agent') or {}).get('name', 'Agent run')))}</h1>
    <div class=\"grid\"><div class=\"card\">Quality Index<br><strong>{summary.get('quality_index', '—')}</strong></div><div class=\"card\">Coverage<br><strong>{summary.get('coverage', 0):.0%}</strong></div><div class=\"card\">Readiness<br><strong>{html.escape(str(summary.get('readiness', '—')))}</strong></div></div>
    <h2>Category profile</h2><table><thead><tr><th>Category</th><th>Score</th><th>Observations</th></tr></thead><tbody>{category_rows}</tbody></table>
    <h2>Provenance</h2><pre>{html.escape(json.dumps({'run_id': run_id, 'configuration_hash': record.configuration_hash, 'created_at': str(record.created_at)}, indent=2))}</pre></body></html>"""
    return HTMLResponse(page)
