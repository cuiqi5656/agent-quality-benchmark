from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import timedelta
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from .models import AgentExecution, BenchmarkCase, TraceEvent, Usage, utc_now


class AdapterError(RuntimeError):
    pass


class UnsafeEndpointError(AdapterError):
    pass


def _host_matches_allowlist(host: str, allowlist: Iterable[str]) -> bool:
    normalized = host.casefold().rstrip(".")
    return any(
        normalized == entry.casefold().strip().rstrip(".")
        or normalized.endswith("." + entry.casefold().strip().lstrip(".").rstrip("."))
        for entry in allowlist
        if entry.strip()
    )


async def validate_endpoint(url: str, allowlist: Iterable[str]) -> tuple[str, ...]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeEndpointError("agent endpoint must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise UnsafeEndpointError("credentials must not be embedded in an agent endpoint URL")
    host = parsed.hostname
    explicitly_allowed = _host_matches_allowlist(host, allowlist)
    if parsed.scheme == "http" and not explicitly_allowed:
        raise UnsafeEndpointError("plain HTTP is allowed only for explicitly allowlisted endpoints")
    try:
        address_infos = await asyncio.to_thread(socket.getaddrinfo, host, parsed.port or 443)
    except socket.gaierror as error:
        raise UnsafeEndpointError("agent endpoint hostname could not be resolved") from error
    addresses: set[str] = set()
    for address_info in address_infos:
        address = ipaddress.ip_address(address_info[4][0])
        addresses.add(str(address))
        unsafe = (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )
        if unsafe and not explicitly_allowed:
            raise UnsafeEndpointError("private and special-use endpoints require an explicit allowlist entry")
    return tuple(sorted(addresses))


async def validate_stable_endpoint(url: str, allowlist: Iterable[str]) -> None:
    first = await validate_endpoint(url, allowlist)
    second = await validate_endpoint(url, allowlist)
    if first != second:
        raise UnsafeEndpointError("agent endpoint DNS changed during validation")


class AgentAdapter(ABC):
    @abstractmethod
    async def execute(self, case: BenchmarkCase, *, repetition: int, seed: int) -> AgentExecution:
        raise NotImplementedError


class AqbHttpAdapter(AgentAdapter):
    def __init__(
        self,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        allowlist: Iterable[str] = (),
        timeout_seconds: float = 120,
    ) -> None:
        self.endpoint = endpoint
        self.headers = headers or {}
        self.allowlist = tuple(allowlist)
        self.timeout_seconds = timeout_seconds

    async def execute(self, case: BenchmarkCase, *, repetition: int, seed: int) -> AgentExecution:
        await validate_stable_endpoint(self.endpoint, self.allowlist)
        request_id = str(uuid.uuid4())
        payload = {
            "protocol_version": "aqb.agent.v1",
            "request_id": request_id,
            "case_id": case.id,
            "seed": seed,
            "messages": case.input.get("messages", [{"role": "user", "content": case.input.get("prompt", "")}]),
            "tools": case.tools,
            "context": case.context,
            "policies": case.policies,
            "limits": {
                "timeout_ms": int(case.limits.get("timeout_ms", self.timeout_seconds * 1_000)),
                "max_turns": int(case.limits.get("max_turns", 12)),
                "max_cost_usd": float(case.limits.get("max_cost_usd", 10)),
            },
            "metadata": {"repetition": repetition},
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(follow_redirects=False, timeout=self.timeout_seconds) as client:
            response = await client.post(self.endpoint, json=payload, headers=self.headers)
        if response.is_redirect:
            raise UnsafeEndpointError("agent endpoint redirects are not followed")
        response.raise_for_status()
        data = response.json()
        if data.get("protocol_version") != "aqb.agent.v1" or data.get("request_id") != request_id:
            raise AdapterError("agent returned an invalid protocol envelope")
        usage = data.get("usage", {})
        usage.setdefault("latency_ms", (time.perf_counter() - started) * 1_000)
        return AgentExecution(
            status=data.get("status", "errored"),
            output=data.get("output", ""),
            final_state=data.get("final_state", {}),
            events=data.get("events", []),
            usage=usage,
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class OpenAICompatibleAdapter(AgentAdapter):
    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        api_key: str | None = None,
        allowlist: Iterable[str] = (),
        timeout_seconds: float = 120,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.allowlist = tuple(allowlist)
        self.timeout_seconds = timeout_seconds

    async def execute(self, case: BenchmarkCase, *, repetition: int, seed: int) -> AgentExecution:
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else self.endpoint + "/chat/completions"
        await validate_stable_endpoint(url, self.allowlist)
        messages = list(case.input.get("messages", [{"role": "user", "content": case.input.get("prompt", "")}]))
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        events: list[TraceEvent] = []
        total_input = 0
        total_output = 0
        started = time.perf_counter()
        max_turns = int(case.limits.get("max_turns", 12))
        tools = [{"type": "function", "function": {key: value for key, value in tool.items() if key in {"name", "description", "parameters"}}} for tool in case.tools]
        fixture_tools = {str(tool.get("name")): tool for tool in case.tools}
        failure_once = str(case.input.get("_aqb_fixture_failure_once", ""))
        tool_attempts: dict[str, int] = {}
        final_output = ""
        status: Literal["succeeded", "failed", "refused", "timed_out", "errored"] = "succeeded"
        async with httpx.AsyncClient(follow_redirects=False, timeout=self.timeout_seconds) as client:
            for turn in range(max_turns):
                payload: dict[str, Any] = {"model": self.model, "messages": messages, "seed": seed}
                if tools:
                    payload["tools"] = tools
                model_started = utc_now()
                response = await client.post(url, json=payload, headers=headers)
                if response.is_redirect:
                    raise UnsafeEndpointError("model endpoint redirects are not followed")
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice["message"]
                usage = data.get("usage", {})
                total_input += int(usage.get("prompt_tokens", 0))
                total_output += int(usage.get("completion_tokens", 0))
                events.append(
                    TraceEvent(
                        event_id=str(uuid.uuid4()),
                        kind="model",
                        name=self.model,
                        started_at=model_started,
                        ended_at=utc_now(),
                        input={"message_count": len(messages)},
                        output={"finish_reason": choice.get("finish_reason")},
                        attributes={"turn": turn + 1},
                    )
                )
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    final_output = message.get("content") or ""
                    break
                messages.append(message)
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    name = str(function.get("name", ""))
                    fixture = fixture_tools.get(name)
                    tool_attempts[name] = tool_attempts.get(name, 0) + 1
                    output: Any
                    if name == failure_once and tool_attempts[name] == 1:
                        output = {"error": "transient_fixture_failure", "retryable": True}
                    else:
                        output = fixture.get("fixture_output") if fixture else {"error": "unknown tool"}
                    events.append(
                        TraceEvent(
                            event_id=str(uuid.uuid4()),
                            kind="tool",
                            name=name,
                            input=function.get("arguments"),
                            output=output,
                            attributes={"allowed": fixture is not None},
                        )
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.get("id"),
                            "content": json.dumps(output),
                        }
                    )
            else:
                status = "failed"
                final_output = "Agent exceeded the configured maximum turns."
        return AgentExecution(
            status=status,
            output=final_output,
            events=events,
            usage=Usage(
                input_tokens=total_input,
                output_tokens=total_output,
                latency_ms=(time.perf_counter() - started) * 1_000,
            ),
            metadata={"harness": "aqb-openai-compatible-v1", "repetition": repetition},
        )


class DemoAdapter(AgentAdapter):
    def __init__(self, strength: str = "strong") -> None:
        if strength not in {"strong", "brittle"}:
            raise ValueError("demo strength must be strong or brittle")
        self.strength = strength

    async def execute(self, case: BenchmarkCase, *, repetition: int, seed: int) -> AgentExecution:
        expected = case.expected
        deterministic_failure = self.strength == "brittle" and (
            sum(ord(character) for character in case.id) + repetition + seed
        ) % 4 == 0
        output = str(expected.get("answer", "Completed"))
        final_state = expected.get("final_state", {})
        events: list[TraceEvent] = []
        available_documents = {str(item.get("id")) for item in case.context}
        for document_id in expected.get("context_required", []):
            if str(document_id) not in available_documents:
                continue
            events.append(
                TraceEvent(
                    event_id=str(uuid.uuid4()),
                    kind="retrieval",
                    name="fixture-search",
                    attributes={"document_ids": [document_id]},
                )
            )
        for tool_name in expected.get("tools_required", []):
            events.append(
                TraceEvent(
                    event_id=str(uuid.uuid4()),
                    kind="tool",
                    name=str(tool_name),
                    input={"case_id": case.id},
                    output={"ok": True},
                )
            )
        if deterministic_failure:
            output = "I could not complete this task."
            final_state = {}
            if case.tags and "security" in case.tags:
                secrets = expected.get("forbidden_secrets", [])
                if secrets:
                    output += " " + str(secrets[0])
        latency: float = 280 + (sum(ord(character) for character in case.id) % 900)
        if self.strength == "brittle":
            latency *= 1.65
        started = utc_now()
        events.insert(
            0,
            TraceEvent(
                event_id=str(uuid.uuid4()),
                kind="agent",
                name=f"demo-{self.strength}",
                started_at=started,
                ended_at=started + timedelta(milliseconds=latency),
                attributes={"deterministic": True},
            ),
        )
        return AgentExecution(
            status="failed" if deterministic_failure else "succeeded",
            output=output,
            final_state=final_state,
            events=events,
            usage=Usage(
                input_tokens=180 + len(case.context) * 45,
                output_tokens=max(10, len(output.split()) * 2),
                cost_usd=0,
                latency_ms=latency,
            ),
            metadata={"demo": True, "strength": self.strength},
        )
