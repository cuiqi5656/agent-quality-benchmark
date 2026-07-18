# Benchmark methodology

AQB evaluates agent systems from observable outcomes toward progressively harder trajectory, robustness, and security questions. A result is a multidimensional evidence profile, not a claim that one score captures every deployment.

## Measurement catalog

| Dimension | Core measurements | Typical evidence |
|---|---|---|
| Outcome | exact/schema/numeric/state correctness, success, completeness, milestones | expected vs actual output/state |
| Adherence | constraints, instruction hierarchy, refusal and escalation | violated rules and policy state |
| Tools | selection precision/recall, arguments, unnecessary calls, loops, recovery, termination | tool spans and final environment state |
| Context | precision/recall, groundedness, citation correctness, omissions, false memory, compression loss | retrieval/memory spans and labeled evidence |
| Reliability | variance, pass@k, strict passᵏ, perturbation sensitivity, failure recovery, ablation deltas | paired repeated trials |
| Safety | injection, canary leakage, authorization, excessive agency, unsafe action, PII, fail-safe behavior | guardrail/tool spans and canaries |
| Efficiency | model/tool/end-to-end latency, tokens, cost/success, retries, errors, throughput, trace completeness | usage and timing spans |
| Conditional | worst-group gaps, language/demographic gaps, freshness/contamination, evaluator quality | suite-specific strata and reviews |

## Evaluation precedence

Deterministic state and rule validators run first. Declarative predicates run second. A calibrated model rubric may fill semantic gaps. A human review can override with attribution. Alternative valid trajectories are not penalized when final state and policy are valid.

Model judges use the Responses API with strict Structured Outputs, isolate case/output/evidence as untrusted data, and record model, prompt, schema, and evaluator version. The configured judge is never silently replaced. Model scores remain visibly uncalibrated until at least 20 blind paired labels achieve Cohen’s κ ≥ 0.60 and disagreement/confusion review is complete.

## Scoring and missingness

Measured observations retain raw units and normalize to 0–100. Balanced v1 weights are outcome 30%, adherence 15%, tools 10%, context 10%, reliability 15%, safety 15%, and efficiency 5%.

The Quality Index is emitted only when at least 80% of configured weight is measurable and both outcome and safety are present. Missing, not-applicable, insufficient-evidence, and evaluator-error states remain distinct; none becomes zero. A critical security, authorization, or leakage failure blocks readiness regardless of aggregate score.

Binary rates use Wilson 95% intervals. Category means use deterministic bootstrap intervals. Aligned run comparisons use paired bootstrap deltas and say “no demonstrated difference” when the interval crosses zero. pass@k estimates whether at least one of k attempts succeeds; strict passᵏ estimates whether all k attempts succeed.

## Robustness and contamination

Suites can define static paraphrase, order, distractor, tool-failure, context-removal, memory-summary, evidence-removal, and tool-exposure variants. Each variant is retained as a trial with a variant ID. Public starter cases are demonstrations with high contamination risk. Release decisions should use versioned private suites, holdouts, freshness dates, and explicit readiness gates.

## Research foundations

The methodology draws on multi-metric scenario evaluation in [HELM](https://arxiv.org/abs/2211.09110), partial-progress diagnosis in [AgentBoard](https://arxiv.org/abs/2401.13178), repeated-trial stateful reliability in [τ-bench](https://arxiv.org/abs/2406.12045), adversarial agent testing in [AgentDojo](https://arxiv.org/abs/2406.13352), and measurement guidance in the [NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/).
