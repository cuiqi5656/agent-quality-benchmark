from aqb_eval.otel import map_otel_spans


def test_otel_genai_span_mapping_preserves_original_payload() -> None:
    payload = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "trace-1",
                                "spanId": "span-1",
                                "name": "chat model",
                                "startTimeUnixNano": "1000000",
                                "endTimeUnixNano": "2000000",
                                "attributes": [{"key": "gen_ai.operation.name", "value": {"stringValue": "chat"}}],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    mapped = map_otel_spans(payload)
    assert mapped["protocol_version"] == "aqb.trace.v1"
    assert mapped["trials"][0]["events"][0]["kind"] == "model"
    assert mapped["raw_source"] == payload
