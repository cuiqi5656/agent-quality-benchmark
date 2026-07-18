# Final setup TODO: optional semantic-judge provider

This is intentionally the last setup action and is **not required** for deterministic starter benchmarks or either demo agent.

- [ ] Choose the semantic-judge provider. OpenAI Responses API support is included; another provider may be substituted by implementing the same strict structured-result adapter contract.
- [ ] Put the selected credential only in the ignored `.env.local` or a deployment secret manager. Never commit it, paste it into logs, or add it to `.env.example`.
- [ ] For the included OpenAI adapter, set `OPENAI_API_KEY`, keep `OPENAI_BASE_URL` explicit, and set `OPENAI_JUDGE_MODEL` to the exact intended model. AQB must fail visibly if that model is unavailable and must never substitute another model silently.
- [ ] If selecting another provider, add a named/versioned adapter, strict output-schema validation, timeout/retry/error tests, cost/usage mapping, and evaluator provenance before enabling it.
- [ ] Run blind judge calibration with at least 20 paired human labels, randomized A/B ordering, agreement/confusion analysis, Cohen's kappa, and disagreement review.
- [ ] Keep judge observations labeled `uncalibrated` until the configured agreement/readiness threshold passes.
- [ ] Re-run secret scanning, unit/integration tests, and a representative private-suite benchmark before using judge-derived scores for release decisions.

Suggested local OpenAI setup, only after a key is selected:

```dotenv
# .env.local — ignored by git
OPENAI_API_KEY=<set-in-secret-store-or-locally>
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_JUDGE_MODEL=gpt-5.6-terra
```

The placeholder above is documentation, not a usable credential.
