from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from .adapters import AgentAdapter
from .judge import JudgeProvider, JudgeUnavailable
from .metrics import evaluate_trial
from .models import AgentProfile, BenchmarkCase, BenchmarkSuite, RunResult, TrialResult
from .scoring import aggregate_run


def _case_variants(case: BenchmarkCase) -> Iterator[tuple[str | None, BenchmarkCase]]:
    """Yield the base case followed by immutable static perturbation/ablation variants."""
    yield None, case
    for perturbation in case.perturbations:
        payload = case.model_dump(mode="python")
        payload["perturbations"] = []
        payload["ablations"] = []
        replacement = perturbation.get("input")
        if isinstance(replacement, dict):
            payload["input"] = {**payload["input"], **replacement}
        if perturbation.get("append"):
            payload["input"]["prompt"] = (
                str(payload["input"].get("prompt", "")) + "\n\n" + str(perturbation["append"])
            ).strip()
        if perturbation.get("tool_failure"):
            payload["input"]["_aqb_fixture_failure_once"] = str(perturbation["tool_failure"])
        yield f"perturbation:{perturbation['id']}", case.__class__.model_validate(payload)
    for ablation in case.ablations:
        payload = case.model_dump(mode="python")
        payload["perturbations"] = []
        payload["ablations"] = []
        for field in ablation.get("remove", []):
            if field in {"context", "tools", "policies"}:
                payload[field] = []
        yield f"ablation:{ablation['id']}", case.__class__.model_validate(payload)


def configuration_hash(agent: AgentProfile, suite: BenchmarkSuite, repetitions: int, seed: int) -> str:
    payload = {
        "agent": agent.model_dump(mode="json", exclude={"credential_ref"}),
        "suite": suite.model_dump(mode="json"),
        "repetitions": repetitions,
        "seed": seed,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


async def execute_run(
    *,
    run_id: str,
    agent: AgentProfile,
    adapter: AgentAdapter,
    suite: BenchmarkSuite,
    repetitions: int,
    seed: int,
    judge: JudgeProvider | None = None,
) -> RunResult:
    result = RunResult(
        run_id=run_id,
        agent=agent,
        suite=suite,
        status="running",
        configuration_hash=configuration_hash(agent, suite, repetitions, seed),
        judge_status="configured" if judge else "disabled",
    )
    try:
        for source_case in suite.cases:
            for variant_id, case in _case_variants(source_case):
                case_repetitions = max(repetitions, case.repetitions)
                for repetition in range(1, case_repetitions + 1):
                    execution = await adapter.execute(case, repetition=repetition, seed=seed + repetition - 1)
                    metrics = evaluate_trial(case, execution)
                    rubric_evaluators = [value for value in case.evaluators if value.get("type") == "model_rubric"]
                    if judge and rubric_evaluators:
                        try:
                            judge_metric = await judge.evaluate(
                                prompt=str(case.input.get("prompt", case.input.get("messages", ""))),
                                output=execution.output,
                                rubric=str(rubric_evaluators[0].get("rubric", "")),
                                evidence=[{"index": index, **item} for index, item in enumerate(case.context)],
                            )
                            metrics.append(judge_metric)
                            result.judge_status = "used"
                        except JudgeUnavailable:
                            result.judge_status = "unavailable"
                    result.trials.append(
                        TrialResult(
                            trial_id=str(uuid.uuid4()),
                            case_id=source_case.id,
                            variant_id=variant_id,
                            repetition=repetition,
                            execution=execution,
                            metrics=metrics,
                        )
                    )
        result.summary = aggregate_run(result.trials, suite)
        result.status = "completed"
        result.completed_at = datetime.now(timezone.utc)
    except Exception as error:
        result.status = "failed"
        result.completed_at = datetime.now(timezone.utc)
        result.metadata["error"] = {"type": type(error).__name__, "message": str(error)}
    return result
