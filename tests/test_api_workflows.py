import json

from aqb_api.main import app
from fastapi.testclient import TestClient


def trace_bundle() -> dict:
    return {
        "protocol_version": "aqb.trace.v1",
        "manifest": {
            "run_id": "external-run",
            "agent": {"name": "<script>alert(1)</script>"},
            "suite": {"id": "aqb.starter.core"},
            "created_at": "2026-07-18T00:00:00Z",
            "configuration_hash": "external-hash",
            "source": "upload",
        },
        "trials": [
            {
                "trial_id": "external-trial",
                "case_id": "output.exact.01",
                "repetition": 1,
                "status": "succeeded",
                "output": "cobalt",
                "events": [],
                "usage": {"latency_ms": 20, "input_tokens": 4, "output_tokens": 1},
            }
        ],
    }


def test_demo_run_idempotency_compare_and_exports() -> None:
    with TestClient(app) as client:
        agents = client.get("/api/v1/agents").json()
        suites = client.get("/api/v1/suites").json()
        assert {agent["id"] for agent in agents} >= {"demo-strong", "demo-brittle"}
        assert suites[0]["case_count"] >= 30

        payload = {
            "agent_id": "demo-strong",
            "suite_id": "suite-starter-core",
            "repetitions": 1,
            "enable_model_judge": False,
            "seed": 9,
        }
        first = client.post(
            "/api/v1/runs", json=payload, headers={"Idempotency-Key": "pytest-demo-run"}
        )
        second = client.post(
            "/api/v1/runs", json=payload, headers={"Idempotency-Key": "pytest-demo-run"}
        )
        assert first.status_code == 202
        assert first.json()["run_id"] == second.json()["run_id"]
        run_id = first.json()["run_id"]
        run = client.get(f"/api/v1/runs/{run_id}").json()
        assert run["status"] == "completed"
        assert run["summary"]["readiness"] == "pass"
        assert run["trials"]

        comparison = client.get(
            "/api/v1/compare",
            params={"baseline_run_id": run_id, "candidate_run_id": run_id},
        ).json()
        assert comparison["quality_index_delta"] == 0
        assert comparison["quality_interval"] == {"low": 0.0, "high": 0.0, "level": 0.95}
        assert comparison["verdict"] == "no demonstrated difference"

        assert client.get(f"/api/v1/reports/{run_id}?format=json").status_code == 200
        csv_response = client.get(f"/api/v1/reports/{run_id}?format=csv")
        assert "metric_key" not in csv_response.text
        assert "task_success" in csv_response.text
        assert client.get(f"/api/v1/reports/{run_id}?format=html").status_code == 200


def test_trace_upload_becomes_run_and_html_escapes_untrusted_content() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/uploads/traces",
            files={"file": ("bundle.json", json.dumps(trace_bundle()), "application/json")},
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["run_id"]
        assert payload["trial_count"] == 1
        run = client.get(f"/api/v1/runs/{payload['run_id']}").json()
        assert run["agent"]["adapter_type"] == "trace_upload"
        report = client.get(f"/api/v1/reports/{payload['run_id']}?format=html").text
        assert "<script>alert(1)</script>" not in report
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report
        assert client.delete(f"/api/v1/runs/{payload['run_id']}").status_code == 204
        assert client.get(f"/api/v1/runs/{payload['run_id']}").status_code == 404


def test_judge_unavailable_is_explicit() -> None:
    with TestClient(app) as client:
        health = client.get("/api/v1/health").json()
        assert health["judge"]["configured"] is False
        assert health["judge"]["status"] == "final setup TODO"
