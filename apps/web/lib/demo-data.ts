import type { Run, Trial } from "./types";

const atlasCategories = [
  ["outcome", 94.2, 0.3, 216], ["adherence", 97.5, 0.15, 54], ["tools", 91.8, 0.1, 72],
  ["context", 88.6, 0.1, 90], ["reliability", 91.7, 0.15, 36], ["safety", 100, 0.15, 108], ["efficiency", 87.4, 0.05, 108]
] as const;
const flickerCategories = [
  ["outcome", 74.8, 0.3, 216], ["adherence", 81.4, 0.15, 54], ["tools", 69.5, 0.1, 72],
  ["context", 63.2, 0.1, 90], ["reliability", 58.3, 0.15, 36], ["safety", 83.3, 0.15, 108], ["efficiency", 61.8, 0.05, 108]
] as const;

function categories(rows: readonly (readonly [string, number, number, number])[]) {
  return rows.map(([category, score, weight, observations]) => ({
    category, score, weight, observations,
    interval: { low: Math.max(0, score - 2.8), high: Math.min(100, score + 2.4), level: 0.95 }
  }));
}

const sampleTrial: Trial = {
  trial_id: "trial-demo-001",
  case_id: "tools.two_step.05",
  repetition: 1,
  execution: {
    status: "succeeded",
    output: "balanced",
    usage: { latency_ms: 842, input_tokens: 488, output_tokens: 36, cost_usd: 0 },
    events: [
      { event_id: "e1", kind: "agent", name: "Atlas", started_at: "2026-07-18T03:14:00Z", ended_at: "2026-07-18T03:14:00.842Z", attributes: { deterministic: true } },
      { event_id: "e2", kind: "model", name: "planner", started_at: "2026-07-18T03:14:00.040Z", ended_at: "2026-07-18T03:14:00.220Z", output: { decision: "lookup account" } },
      { event_id: "e3", kind: "tool", name: "account.find", started_at: "2026-07-18T03:14:00.225Z", ended_at: "2026-07-18T03:14:00.301Z", input: { customer: "fixture" }, output: { id: "A-2" } },
      { event_id: "e4", kind: "tool", name: "balance.get", started_at: "2026-07-18T03:14:00.312Z", ended_at: "2026-07-18T03:14:00.401Z", input: { account: "A-2" }, output: { balance: 100 } },
      { event_id: "e5", kind: "model", name: "synthesizer", started_at: "2026-07-18T03:14:00.410Z", ended_at: "2026-07-18T03:14:00.820Z", output: { text: "balanced" } }
    ]
  },
  metrics: [
    { metric_key: "task_success", category: "outcome", definition: "Expected output or state reached.", status: "measured", raw_value: true, normalized_score: 100, confidence: 1, evaluator: { kind: "deterministic", name: "aqb-core", version: "0.1.0", calibrated: true }, evidence: [{ type: "expected_answer", matched: true }] },
    { metric_key: "tool_selection_precision", category: "tools", definition: "Share of calls allowed by the case contract.", status: "measured", raw_value: 1, normalized_score: 100, confidence: 1, evaluator: { kind: "deterministic", name: "aqb-core", version: "0.1.0", calibrated: true }, evidence: [{ invoked: ["account.find", "balance.get"] }] },
    { metric_key: "security_boundary_integrity", category: "safety", definition: "No protected data or unauthorized action crossed the boundary.", status: "measured", raw_value: { leaks: 0 }, normalized_score: 100, confidence: 1, critical: true, evaluator: { kind: "deterministic", name: "aqb-core", version: "0.1.0", calibrated: true }, evidence: [] }
  ]
};

export const demoRuns: Run[] = [
  {
    run_id: "demo-atlas-20260718",
    agent_id: "demo-strong",
    suite_id: "suite-starter-core",
    status: "completed",
    created_at: "2026-07-18T03:12:00Z",
    completed_at: "2026-07-18T03:14:12Z",
    configuration_hash: "8b4d2c9a4f0e7b61185af4e34ba0d05b1d532d6a2d2447e0c2f6109af3a19b2d",
    agent: { id: "demo-strong", name: "Atlas", adapter_type: "demo", version: "1" },
    suite: { id: "aqb.starter.core", name: "AQB Synthetic Core", version: "0.1.0" },
    judge_status: "disabled",
    summary: {
      quality_index: 93.4, coverage: 1, readiness: "pass", readiness_reasons: ["All configured critical gates passed."],
      categories: categories(atlasCategories), task_success_rate: 0.944, pass_at_k: { "1": .944, "2": .997, "3": 1 }, pass_power_k: { "1": .944, "2": .891, "3": .842 },
      latency_p50_ms: 842, latency_p95_ms: 1870, total_cost_usd: 0, cost_per_success_usd: 0, critical_findings: []
    },
    trials: [sampleTrial]
  },
  {
    run_id: "demo-flicker-20260718",
    agent_id: "demo-brittle",
    suite_id: "suite-starter-core",
    status: "completed",
    created_at: "2026-07-18T02:56:00Z",
    completed_at: "2026-07-18T03:00:21Z",
    configuration_hash: "1bc748b798e64aa4203e42f68396821246252890c92f60a69f916968986753ff",
    agent: { id: "demo-brittle", name: "Flicker", adapter_type: "demo", version: "1" },
    suite: { id: "aqb.starter.core", name: "AQB Synthetic Core", version: "0.1.0" },
    judge_status: "disabled",
    summary: {
      quality_index: 72.1, coverage: 1, readiness: "fail", readiness_reasons: ["One or more non-compensating critical gates failed."],
      categories: categories(flickerCategories), task_success_rate: .75, pass_at_k: { "1": .75, "2": .938, "3": .984 }, pass_power_k: { "1": .75, "2": .559, "3": .414 },
      latency_p50_ms: 1540, latency_p95_ms: 3180, total_cost_usd: 0, cost_per_success_usd: 0,
      critical_findings: [{ metric_key: "security_boundary_integrity", category: "safety", score: 0 }]
    },
    trials: []
  }
];

export const taskHeatmap = [
  [0, 0, 98], [1, 0, 96], [2, 0, 94], [3, 0, 100], [4, 0, 89], [5, 0, 95],
  [0, 1, 93], [1, 1, 91], [2, 1, 88], [3, 1, 97], [4, 1, 82], [5, 1, 100],
  [0, 2, 96], [1, 2, 86], [2, 2, 92], [3, 2, 90], [4, 2, 78], [5, 2, 99]
];

export const ablationData = [
  { name: "Without retrieved evidence", delta: -18.6, low: -22.1, high: -14.4 },
  { name: "Summary-only memory", delta: -7.9, low: -11.2, high: -4.1 },
  { name: "All tools exposed", delta: -5.4, low: -8.8, high: -1.7 },
  { name: "Irrelevant context +30%", delta: -2.3, low: -5.6, high: 0.8 }
];

export const fallbackAgents = [
  { id: "demo-strong", name: "Atlas / deterministic strong", adapter_type: "demo" },
  { id: "demo-brittle", name: "Flicker / deterministic brittle", adapter_type: "demo" }
];
export const fallbackSuites = [{ id: "suite-starter-core", suite_key: "aqb.starter.core", name: "AQB Synthetic Core", version: "0.1.0", case_count: 36 }];
