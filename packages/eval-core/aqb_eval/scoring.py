from __future__ import annotations

from collections import defaultdict
from typing import Literal

from .metrics import DETERMINISTIC, successful
from .models import (
    BenchmarkSuite,
    Category,
    CategoryScore,
    MetricObservation,
    RunSummary,
    TrialResult,
)
from .stats import bootstrap_mean_interval, mean, pass_at_k, pass_power_k, percentile


def _reliability_metrics(trials: list[TrialResult]) -> list[MetricObservation]:
    by_case: dict[str, list[bool]] = defaultdict(list)
    for trial in trials:
        key = f"{trial.case_id}:{trial.variant_id or 'base'}"
        by_case[key].append(successful(trial.metrics))
    if not by_case:
        return []
    strict_rates = [1.0 if all(results) else 0.0 for results in by_case.values()]
    score = mean(strict_rates) * 100
    return [
        MetricObservation(
            metric_key="repeatability",
            category=Category.RELIABILITY,
            definition="Share of cases that succeeded in every configured repetition.",
            status="measured",
            raw_value=mean(strict_rates),
            normalized_score=score,
            confidence=1.0,
            interval=bootstrap_mean_interval([value * 100 for value in strict_rates]),
            evaluator=DETERMINISTIC,
            evidence=[{"type": "case_repetitions", "cases": len(by_case)}],
        )
    ]


def aggregate_run(trials: list[TrialResult], suite: BenchmarkSuite) -> RunSummary:
    reliability_observations = _reliability_metrics(trials)
    observations = [metric for trial in trials for metric in trial.metrics] + reliability_observations
    measured_by_category: dict[Category, list[MetricObservation]] = defaultdict(list)
    for observation in observations:
        if observation.status == "measured" and observation.normalized_score is not None:
            measured_by_category[observation.category].append(observation)

    total_weight = sum(suite.profile.weights.values())
    measured_weight = sum(
        weight for category, weight in suite.profile.weights.items() if measured_by_category.get(category)
    )
    coverage = measured_weight / total_weight if total_weight else 0.0
    category_scores: list[CategoryScore] = []
    weighted_total = 0.0
    for category, weight in suite.profile.weights.items():
        category_observations = measured_by_category.get(category, [])
        if not category_observations:
            continue
        values = [float(metric.normalized_score) for metric in category_observations if metric.normalized_score is not None]
        category_score = mean(values)
        weighted_total += category_score * weight
        category_scores.append(
            CategoryScore(
                category=category,
                score=round(category_score, 2),
                weight=weight,
                observations=len(values),
                interval=bootstrap_mean_interval(values),
            )
        )

    required_present = all(measured_by_category.get(category) for category in suite.profile.required_categories)
    quality_index = None
    if coverage >= suite.profile.minimum_coverage and required_present and measured_weight:
        quality_index = round(weighted_total / measured_weight, 2)

    critical_findings = [
        {
            "metric_key": metric.metric_key,
            "category": metric.category.value,
            "score": metric.normalized_score,
            "evidence": metric.evidence,
        }
        for metric in observations
        if metric.critical and metric.status == "measured" and (metric.normalized_score or 0) < 100
    ]
    readiness_reasons: list[str] = []
    if critical_findings:
        readiness_reasons.append("One or more non-compensating critical gates failed.")
    if quality_index is None:
        readiness_reasons.append("The configured evidence coverage threshold was not met.")

    task_successes = [successful(trial.metrics) for trial in trials]
    success_count = sum(task_successes)
    total_trials = len(trials)
    grouped = _group_successes(trials)
    reliability_k = min(max((len(values) for values in grouped.values()), default=1), 10)
    pass_at = {
        str(k): round(mean([pass_at_k(sum(values), len(values), k) for values in grouped.values()]), 4)
        for k in range(1, reliability_k + 1)
    }
    pass_power = {
        str(k): round(mean([pass_power_k(sum(values), len(values), k) for values in grouped.values()]), 4)
        for k in range(1, reliability_k + 1)
    }
    latencies = [trial.execution.usage.latency_ms for trial in trials]
    total_cost = sum(trial.execution.usage.cost_usd for trial in trials)

    if quality_index is None:
        readiness: Literal["pass", "fail", "insufficient_evidence"] = "insufficient_evidence"
    elif critical_findings:
        readiness = "fail"
    else:
        readiness = "pass"
        readiness_reasons.append("All configured critical gates passed.")

    return RunSummary(
        quality_index=quality_index,
        coverage=round(coverage, 4),
        readiness=readiness,
        readiness_reasons=readiness_reasons,
        categories=category_scores,
        task_success_rate=round(success_count / total_trials, 4) if total_trials else 0.0,
        pass_at_k=pass_at,
        pass_power_k=pass_power,
        latency_p50_ms=round(percentile(latencies, 0.5), 2),
        latency_p95_ms=round(percentile(latencies, 0.95), 2),
        total_cost_usd=round(total_cost, 6),
        cost_per_success_usd=round(total_cost / success_count, 6) if success_count else None,
        critical_findings=critical_findings,
    )


def _group_successes(trials: list[TrialResult]) -> dict[str, list[bool]]:
    result: dict[str, list[bool]] = defaultdict(list)
    for trial in trials:
        key = f"{trial.case_id}:{trial.variant_id or 'base'}"
        result[key].append(successful(trial.metrics))
    return result
