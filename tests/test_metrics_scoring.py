from aqb_eval.metrics import evaluate_trial
from aqb_eval.models import (
    AgentExecution,
    BenchmarkCase,
    BenchmarkSuite,
    ScoreProfile,
    TraceEvent,
    TrialResult,
)
from aqb_eval.scoring import aggregate_run


def case(**changes):
    payload = {
        "id": "case-1",
        "category": "test",
        "input": {"prompt": "say ok"},
        "expected": {"answer": "ok"},
    }
    payload.update(changes)
    return BenchmarkCase.model_validate(payload)


def execution(**changes):
    payload = {"status": "succeeded", "output": "ok", "usage": {"latency_ms": 100}}
    payload.update(changes)
    return AgentExecution.model_validate(payload)


def test_na_is_preserved_instead_of_zero() -> None:
    metrics = evaluate_trial(case(), execution())
    adherence = next(metric for metric in metrics if metric.metric_key == "instruction_adherence")
    tools = next(metric for metric in metrics if metric.metric_key == "tool_selection_precision")
    assert adherence.status == "not_applicable" and adherence.normalized_score is None
    assert tools.status == "not_applicable" and tools.normalized_score is None


def test_tool_context_and_security_metrics_attach_evidence() -> None:
    benchmark_case = case(
        expected={
            "answer": "ok",
            "tools_required": ["lookup"],
            "tools_allowed": ["lookup"],
            "context_required": ["doc-1"],
            "forbidden_secrets": ["CANARY"],
        },
        context=[{"id": "doc-1", "content": "evidence"}],
        tags=["security"],
    )
    agent_execution = execution(
        events=[
            TraceEvent(event_id="t", kind="tool", name="lookup"),
            TraceEvent(
                event_id="r",
                kind="retrieval",
                name="search",
                attributes={"document_ids": ["doc-1"]},
            ),
        ]
    )
    metrics = evaluate_trial(benchmark_case, agent_execution)
    by_key = {metric.metric_key: metric for metric in metrics}
    assert by_key["tool_selection_precision"].normalized_score == 100
    assert by_key["tool_selection_recall"].normalized_score == 100
    assert by_key["context_precision"].normalized_score == 100
    assert by_key["context_recall"].normalized_score == 100
    assert by_key["security_boundary_integrity"].critical is True
    assert by_key["security_boundary_integrity"].evidence


def test_critical_gate_is_non_compensating() -> None:
    benchmark_case = case(
        expected={"answer": "ok", "forbidden_secrets": ["CANARY"]}, tags=["security"]
    )
    unsafe = execution(output="ok CANARY")
    metrics = evaluate_trial(benchmark_case, unsafe)
    trial = TrialResult(trial_id="trial", case_id=benchmark_case.id, execution=unsafe, metrics=metrics)
    suite = BenchmarkSuite(
        id="suite",
        name="suite",
        version="1",
        cases=[benchmark_case],
        profile=ScoreProfile(
            weights={"outcome": 0.6, "safety": 0.4},
            minimum_coverage=0.8,
            required_categories=["outcome", "safety"],
        ),
    )
    summary = aggregate_run([trial], suite)
    assert summary.quality_index is not None
    assert summary.readiness == "fail"
    assert summary.critical_findings[0]["metric_key"] == "security_boundary_integrity"


def test_missing_required_category_suppresses_quality_index() -> None:
    benchmark_case = case()
    result = execution()
    metrics = [metric for metric in evaluate_trial(benchmark_case, result) if metric.category.value == "outcome"]
    trial = TrialResult(trial_id="trial", case_id=benchmark_case.id, execution=result, metrics=metrics)
    suite = BenchmarkSuite(id="suite", name="suite", version="1", cases=[benchmark_case])
    summary = aggregate_run([trial], suite)
    assert summary.quality_index is None
    assert summary.readiness == "insufficient_evidence"
