# Security policy

## Reporting

Do not open a public issue for a vulnerability. Use GitHub private vulnerability reporting for `cuiqi5656/agent-quality-benchmark`. Include affected version, reproduction, impact, and a suggested remediation if available. Expect acknowledgement within five business days.

## Supported versions

Only the latest tagged release receives security fixes during the v0.x phase.

## Threat model and controls

- Uploads are data only. AQB never executes uploaded code. JSON/JSONL parsing is bounded; ZIP members reject traversal, absolute paths, symlinks, unsupported suffixes, excessive entry count, expansion, and compression ratio.
- Live endpoints are validated for scheme, embedded credentials, DNS stability, private/special-use addresses, redirects, and explicit local allowlisting. Production deployments should enforce a narrow egress policy at the network layer as defense in depth.
- Endpoint credentials require a Fernet key, are encrypted at rest, and are never returned. Trace content is escaped in the UI and configured secret/PII patterns are redacted.
- Judge prompts isolate trace and rubric payloads as untrusted data. Judge output must satisfy a strict schema and stays uncalibrated until reviewed.
- Docker publishes only the web service on `127.0.0.1`. Remote access requires TLS and an authenticated reverse proxy.
- Run deletion removes dependent observations, reviews, and stored artifacts.

## Deployment checklist

Generate `AQB_ENCRYPTION_KEY`, restrict endpoint allowlists, place PostgreSQL/Redis on an internal network, keep images patched, enable authenticated TLS termination, back up encrypted data, and define a retention policy. Never reuse the demonstration database password for a remote deployment.
