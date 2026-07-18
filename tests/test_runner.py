import pytest
from aqb_eval.adapters import DemoAdapter
from aqb_eval.models import AgentProfile
from aqb_eval.runner import configuration_hash, execute_run
from aqb_eval.suites import load_suite


@pytest.mark.asyncio
async def test_demo_run_executes_repetitions_perturbations_and_ablations() -> None:
    suite = load_suite("benchmark-packs/starter/core.yaml")
    agent = AgentProfile(id="strong", name="Strong", adapter_type="demo")
    result = await execute_run(
        run_id="run",
        agent=agent,
        adapter=DemoAdapter("strong"),
        suite=suite,
        repetitions=2,
        seed=7,
    )
    variant_count = sum(len(case.perturbations) + len(case.ablations) for case in suite.cases)
    assert len(result.trials) == (len(suite.cases) + variant_count) * 2 + 1
    assert any(trial.variant_id and trial.variant_id.startswith("ablation:") for trial in result.trials)
    assert any(trial.variant_id and trial.variant_id.startswith("perturbation:") for trial in result.trials)
    assert result.status == "completed"
    assert result.summary is not None
    assert result.summary.readiness == "pass"
    assert result.summary.coverage == 1
    assert result.summary.pass_power_k["2"] == 1


def test_configuration_hash_excludes_credential_reference() -> None:
    suite = load_suite("benchmark-packs/starter/core.yaml")
    left = AgentProfile(id="agent", name="A", adapter_type="demo", credential_ref="secret-a")
    right = AgentProfile(id="agent", name="A", adapter_type="demo", credential_ref="secret-b")
    assert configuration_hash(left, suite, 3, 42) == configuration_hash(right, suite, 3, 42)
