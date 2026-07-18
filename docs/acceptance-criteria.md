# v0.1.0 acceptance criteria

## Repository and publication

- [x] Public MIT repository at `cuiqi5656/agent-quality-benchmark`, default branch `main`.
- [x] README, architecture/methodology/protocol docs, contributing, conduct, security, support, changelog, citation, templates, and Dependabot are present.
- [x] Required CI, CodeQL, Docker integration, dependency-audit, and container-scan checks are green on GitHub.
- [ ] v0.1.0 is released only after the final report commit passes and `main` protection is active.

## Product and evaluation

- [x] Trace upload, OpenAI-compatible, and AQB HTTP touchpoints use versioned contracts.
- [x] At least 30 deterministic synthetic cases and two no-cost demo agents produce meaningful results.
- [x] Outcomes, adherence, tools, context, reliability, safety, efficiency, perturbations, and ablations are implemented.
- [x] Every observation exposes definition, raw value, evidence, evaluator/version, applicability, normalized score, and confidence/uncertainty where meaningful.
- [x] Coverage, Quality Index, readiness gates, reliability, paired comparison, and ablation views follow stored observations.
- [x] Optional judging fails explicitly when unavailable and never silently substitutes a model.

## Experience and export

- [x] Guided connect/upload → suite → policy → run → dashboard → compare/review/export flow exists.
- [x] Dashboard, trace waterfall, calibration, builder contract, and print view are responsive and keyboard-addressable.
- [x] Charts have accessible names and table equivalents; reduced motion and print CSS are present.
- [x] JSON manifest/results, CSV observations, and self-contained HTML reports are supported.
- [x] Lighthouse accessibility score ≥ 90 is recorded (100/100 in `docs/lighthouse-accessibility.json`).

## Security and operations

- [x] Only the web service binds to localhost in Compose; PostgreSQL, Redis, API, and worker stay internal.
- [x] Uploaded code is never executed; archive traversal, symlink, unsupported type, size, expansion, and compression-ratio attacks are tested.
- [x] Endpoint scheme, DNS stability, private/special-use targets, embedded credentials, and redirects are controlled.
- [x] Credential storage requires encryption; redaction, escaped trace content, prompt isolation, and permanent run/artifact deletion are present.
- [x] `docker compose up --build --wait`, container health, UI, and proxied API health are verified in the hosted release environment.
- [x] Python and production npm audits report no known vulnerabilities.
- [x] No unresolved high/critical container findings remain.

## Validation

- [x] Python unit/integration/security/API/adapter tests pass.
- [x] Python lint and strict type checks pass.
- [x] Frontend lint, TypeScript, unit tests, production build, and Playwright product flows pass.
- [x] Migration upgrade/downgrade/upgrade passes against an isolated database.
- [x] Full Docker integration passes.
- [x] GitHub Actions, CodeQL, dependency audit, and Trivy pass remotely.

## Explicitly deferred post-release setup

- [ ] Select and calibrate an optional semantic-judge provider/key using `docs/final-setup-todo.md`. The owner explicitly deferred this provider choice; deterministic benchmarks and explicit unavailable-judge behavior remain release-ready.

The release checkbox is the only remaining v0.1.0 publication gate. The provider/key checkbox is an owner-deferred post-release integration task, not an implied success or release blocker.
