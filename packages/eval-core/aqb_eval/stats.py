from __future__ import annotations

import math
import random
from collections.abc import Sequence

from .models import ConfidenceInterval


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: Sequence[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> ConfidenceInterval:
    if total <= 0:
        return ConfidenceInterval(low=0, high=0)
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = proportion + z * z / (2 * total)
    adjustment = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total)
    return ConfidenceInterval(
        low=max(0.0, (centre - adjustment) / denominator),
        high=min(1.0, (centre + adjustment) / denominator),
    )


def bootstrap_mean_interval(
    values: Sequence[float], *, samples: int = 2_000, seed: int = 42
) -> ConfidenceInterval | None:
    if not values:
        return None
    if len(values) == 1:
        return ConfidenceInterval(low=float(values[0]), high=float(values[0]))
    rng = random.Random(seed)  # noqa: S311 - deterministic statistical resampling, not security
    estimates = [mean([rng.choice(values) for _ in values]) for _ in range(samples)]
    return ConfidenceInterval(low=percentile(estimates, 0.025), high=percentile(estimates, 0.975))


def paired_bootstrap_delta(
    baseline: Sequence[float], candidate: Sequence[float], *, samples: int = 2_000, seed: int = 42
) -> tuple[float, ConfidenceInterval]:
    if len(baseline) != len(candidate) or not baseline:
        raise ValueError("paired comparison requires equally sized, non-empty samples")
    deltas = [candidate[index] - baseline[index] for index in range(len(baseline))]
    interval = bootstrap_mean_interval(deltas, samples=samples, seed=seed)
    assert interval is not None
    return mean(deltas), interval


def pass_at_k(successes: int, total: int, k: int) -> float:
    """Probability at least one of k draws succeeds, without replacement."""
    if not 1 <= k <= total:
        return 0.0
    failures = total - successes
    if failures < k:
        return 1.0
    return 1 - math.comb(failures, k) / math.comb(total, k)


def pass_power_k(successes: int, total: int, k: int) -> float:
    """Strict reliability: probability every one of k draws succeeds."""
    if not 1 <= k <= total or successes < k:
        return 0.0
    return math.comb(successes, k) / math.comb(total, k)


def cohen_kappa(left: Sequence[str], right: Sequence[str]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("kappa requires equally sized, non-empty label sequences")
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    labels = sorted(set(left) | set(right))
    expected = sum((left.count(label) / len(left)) * (right.count(label) / len(right)) for label in labels)
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)
