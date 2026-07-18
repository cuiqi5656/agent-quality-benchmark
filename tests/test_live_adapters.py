import json

import httpx
import pytest
from aqb_eval import adapters
from aqb_eval.adapters import AqbHttpAdapter, OpenAICompatibleAdapter
from aqb_eval.models import BenchmarkCase


def benchmark_case() -> BenchmarkCase:
    return BenchmarkCase(
        id="live.case",
        category="tools",
        input={"prompt": "Look up the fixture and answer done."},
        expected={"answer": "done", "tools_required": ["fixture.get"]},
        tools=[
            {
                "name": "fixture.get",
                "description": "read fixture",
                "parameters": {"type": "object"},
                "fixture_output": {"ok": True},
            }
        ],
    )


@pytest.mark.asyncio
async def test_aqb_http_contract_happy_path(monkeypatch) -> None:
    async def validated(*_args, **_kwargs) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "protocol_version": "aqb.agent.v1",
                "request_id": body["request_id"],
                "status": "succeeded",
                "output": "done",
                "events": [],
                "usage": {"input_tokens": 3, "output_tokens": 1},
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(adapters, "validate_stable_endpoint", validated)
    monkeypatch.setattr(
        adapters.httpx,
        "AsyncClient",
        lambda **_kwargs: real_client(transport=httpx.MockTransport(handler)),
    )
    result = await AqbHttpAdapter("https://agent.example/run").execute(
        benchmark_case(), repetition=1, seed=7
    )
    assert result.status == "succeeded"
    assert result.output == "done"
    assert result.usage.latency_ms > 0


@pytest.mark.asyncio
async def test_openai_compatible_versioned_tool_loop(monkeypatch) -> None:
    async def validated(*_args, **_kwargs) -> None:
        return None

    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {"name": "fixture.get", "arguments": "{}"},
                                    }
                                ],
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "done"},
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 1},
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(adapters, "validate_stable_endpoint", validated)
    monkeypatch.setattr(
        adapters.httpx,
        "AsyncClient",
        lambda **_kwargs: real_client(transport=httpx.MockTransport(handler)),
    )
    result = await OpenAICompatibleAdapter(
        "https://models.example/v1", "fixture-model"
    ).execute(benchmark_case(), repetition=1, seed=7)
    assert result.output == "done"
    assert [event.kind for event in result.events] == ["model", "tool", "model"]
    assert result.usage.input_tokens == 22
