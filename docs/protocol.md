# Protocol and API

The canonical schemas are in `packages/protocol/schemas`. Breaking changes receive a new protocol identifier; compatible additions preserve existing identifiers.

## Agent touchpoints

### AQB HTTP (`aqb.agent.v1`)

AQB POSTs a request ID, case ID, seed, messages, fixture tools, context, policies, limits, and repetition metadata. The synchronous response echoes the protocol/request ID and returns status, output, final state, events, usage, error, and metadata. Redirects are not followed.

### OpenAI-compatible

AQB calls `/chat/completions` with a versioned fixture-tool loop. Fixture tools return declared static outputs; uploaded or returned code is never executed. The harness records model and tool spans, token usage, maximum turns, and deterministic seed when supported.

### Trace upload (`aqb.trace.v1`)

JSON uses a bundle object. JSONL treats each line as a trial. ZIP accepts `bundle.json`, or `manifest.json` plus `trials.jsonl`. A manifest identifies source agent/suite, created time, runner, and configuration hash. Trials contain case/variant/repetition, status, output/state, events, usage, optional observations, and retained raw source. Compatible OpenTelemetry GenAI spans map into this shape while the original payload is retained.

## Suite (`aqb.suite.v1`)

A suite defines immutable cases with inputs, tools, context, policies, expected output/state, evaluator configuration, budgets, repetitions, perturbations, ablations, tags, score profile, provenance, and readiness gates. Create a new version rather than editing a suite used by an existing run.

## REST surface

All resources are under `/api/v1`: health, agents and connection tests, suites and YAML import, trace/OpenTelemetry uploads, runs and SSE events, comparisons, human reviews, calibration, reports, and permanent run deletion. Run creation supports `Idempotency-Key`. FastAPI serves generated OpenAPI at `/docs` and `/openapi.json` when the API is accessed directly inside the trusted network.
