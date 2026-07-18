from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _iso_from_nanos(value: int | str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=timezone.utc).isoformat()


def map_otel_spans(payload: dict[str, Any]) -> dict[str, Any]:
    """Map common OTLP/GenAI span fields while retaining the complete source payload."""
    trials: list[dict[str, Any]] = []
    for resource_span in payload.get("resourceSpans", []):
        for scope_span in resource_span.get("scopeSpans", []):
            spans = scope_span.get("spans", [])
            if not spans:
                continue
            events: list[dict[str, Any]] = []
            input_tokens = 0
            output_tokens = 0
            for span in spans:
                attributes = {
                    item.get("key"): next(iter(item.get("value", {}).values()), None)
                    for item in span.get("attributes", [])
                }
                operation = str(attributes.get("gen_ai.operation.name", span.get("name", "agent")))
                if "tool" in operation:
                    kind = "tool"
                elif "retriev" in operation:
                    kind = "retrieval"
                elif operation.casefold() in {"chat", "text_completion", "embeddings"}:
                    kind = "model"
                else:
                    kind = "model" if attributes.get("gen_ai.request.model") else "agent"
                input_tokens += int(attributes.get("gen_ai.usage.input_tokens") or 0)
                output_tokens += int(attributes.get("gen_ai.usage.output_tokens") or 0)
                events.append(
                    {
                        "event_id": span.get("spanId", str(uuid.uuid4())),
                        "parent_event_id": span.get("parentSpanId") or None,
                        "kind": kind,
                        "name": span.get("name", operation),
                        "started_at": _iso_from_nanos(span.get("startTimeUnixNano")),
                        "ended_at": _iso_from_nanos(span.get("endTimeUnixNano")),
                        "attributes": attributes,
                        "input": None,
                        "output": None,
                    }
                )
            trials.append(
                {
                    "trial_id": str(uuid.uuid4()),
                    "case_id": "otel-import",
                    "repetition": 1,
                    "status": "succeeded",
                    "output": "",
                    "events": events,
                    "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
                    "raw_source": spans,
                }
            )
    return {
        "protocol_version": "aqb.trace.v1",
        "manifest": {
            "run_id": str(uuid.uuid4()),
            "agent": {"name": "OpenTelemetry import"},
            "suite": {"name": "Imported traces"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "runner_version": "otel-mapper-v1",
            "configuration_hash": "imported",
            "source": "otel",
        },
        "trials": trials,
        "raw_source": payload,
    }
