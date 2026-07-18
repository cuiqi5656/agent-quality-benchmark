# AQB protocol package

This directory is the canonical, versioned wire contract shared by the runner, API, agents, importers, and UI. Schemas are additive within `v1`; breaking changes require a new protocol version.

- `aqb.agent.v1.schema.json` — live AQB HTTP request/response envelope
- `aqb.trace.v1.schema.json` — portable run and trace bundle
- `aqb.suite.v1.schema.json` — benchmark suite definition
- `aqb.metric.v1.schema.json` — evidence-bearing metric observation
