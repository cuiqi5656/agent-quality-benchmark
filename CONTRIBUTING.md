# Contributing

Thank you for improving Agent Quality Benchmark. AQB is evidence infrastructure, so correctness, provenance, security, and reproducibility take precedence over adding a large number of metrics.

## Development setup

1. Install Node 22+, pnpm 11.9, Python 3.10+, uv 0.11, and Docker.
2. Run `cp .env.example .env.local`. Generate `AQB_ENCRYPTION_KEY` before storing endpoint credentials; the optional judge key can remain blank.
3. Run `pnpm install` and `uv sync --dev`.
4. Run `make check` before opening a pull request.

## Change expectations

- Add deterministic tests for every scoring, applicability, gate, or protocol change.
- Version public schemas and evaluators; do not silently alter historical meaning.
- Preserve missing and not-applicable values instead of coercing them to zero.
- Never include secrets, private benchmark data, model outputs containing personal data, or copyrighted datasets without permission.
- Document threat-model changes in `SECURITY.md`.

Use focused commits and the pull request template. By participating, you agree to the Code of Conduct and certify that you have the right to submit your contribution under the MIT license.
