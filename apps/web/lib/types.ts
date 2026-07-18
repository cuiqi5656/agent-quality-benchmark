export type CategoryScore = {
  category: string;
  score: number;
  weight: number;
  observations: number;
  interval?: { low: number; high: number; level: number } | null;
};

export type RunSummary = {
  quality_index: number | null;
  coverage: number;
  readiness: "pass" | "fail" | "insufficient_evidence";
  readiness_reasons: string[];
  categories: CategoryScore[];
  task_success_rate: number;
  pass_at_k: Record<string, number>;
  pass_power_k: Record<string, number>;
  latency_p50_ms: number;
  latency_p95_ms: number;
  total_cost_usd: number;
  cost_per_success_usd: number | null;
  critical_findings: Array<Record<string, unknown>>;
};

export type Metric = {
  metric_key: string;
  category: string;
  definition: string;
  status: string;
  raw_value: unknown;
  normalized_score: number | null;
  confidence?: number | null;
  critical?: boolean;
  evidence?: Array<Record<string, unknown>>;
  evaluator?: { kind: string; name: string; version: string; calibrated?: boolean };
};

export type TraceEvent = {
  event_id: string;
  kind: string;
  name: string;
  started_at: string;
  ended_at?: string | null;
  input?: unknown;
  output?: unknown;
  attributes?: Record<string, unknown>;
};

export type Trial = {
  trial_id: string;
  case_id: string;
  repetition: number;
  execution: {
    status: string;
    output: string;
    events: TraceEvent[];
    usage: { latency_ms: number; input_tokens: number; output_tokens: number; cost_usd: number };
  };
  metrics: Metric[];
};

export type Run = {
  run_id: string;
  agent_id?: string;
  suite_id?: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  configuration_hash?: string;
  agent?: { id: string; name: string; adapter_type: string; version?: string };
  suite?: { id: string; name: string; version: string; cases?: unknown[] };
  summary: RunSummary | null;
  trials?: Trial[];
  judge_status?: string;
};

export type Agent = { id: string; name: string; adapter_type: string; model?: string; endpoint?: string };
export type Suite = { id: string; suite_key: string; name: string; version: string; case_count: number; provenance?: Record<string, unknown> };
