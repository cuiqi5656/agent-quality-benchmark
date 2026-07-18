from aqb_eval.stats import (
    cohen_kappa,
    paired_bootstrap_delta,
    pass_at_k,
    pass_power_k,
    percentile,
    wilson_interval,
)


def test_wilson_interval_contains_observed_rate() -> None:
    interval = wilson_interval(8, 10)
    assert interval.low < 0.8 < interval.high
    assert 0 <= interval.low <= interval.high <= 1


def test_reliability_formulas_distinguish_recovery_and_consistency() -> None:
    assert pass_at_k(2, 3, 2) == 1
    assert pass_power_k(2, 3, 2) == 1 / 3
    assert pass_at_k(0, 3, 1) == 0
    assert pass_power_k(3, 3, 3) == 1


def test_paired_bootstrap_and_percentile_are_deterministic() -> None:
    delta, interval = paired_bootstrap_delta([10, 20, 30], [15, 25, 35], seed=7)
    assert delta == 5
    assert interval.low == interval.high == 5
    assert percentile([1, 2, 3, 4], 0.5) == 2.5


def test_cohen_kappa() -> None:
    assert cohen_kappa(["pass", "fail"], ["pass", "fail"]) == 1
