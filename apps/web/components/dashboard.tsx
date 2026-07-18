import Link from "next/link";
import { ArrowRight, CheckCircle2, CircleDollarSign, Clock3, Gauge, ShieldAlert, Sparkles } from "lucide-react";
import { formatCurrency, formatDuration, formatPercent } from "../lib/format";
import type { Run } from "../lib/types";
import { CategoryChart, HeatmapChart, ParetoChart, ReliabilityChart } from "./charts";

export function Dashboard({ runs }: { runs: Run[] }) {
  const run = runs[0];
  const summary = run.summary!;
  return (
    <div className="page">
      <div className="page-head">
        <div><div className="eyebrow">Evidence over intuition</div><h1>Agent quality, made legible.</h1><p className="lede">Reproducible evaluation across outcomes, trajectories, context, reliability, safety, and efficiency—with evidence attached to every score.</p></div>
        <div className="run-meta"><span className="badge good"><CheckCircle2 size={13} /> latest run ready</span><span>{run.agent?.name} · {run.suite?.version}</span></div>
      </div>
      <section className="metric-grid" aria-label="Key benchmark metrics">
        <Metric label="Quality Index" value={summary.quality_index?.toFixed(1) ?? "—"} caption={`${formatPercent(summary.coverage)} measurable`} primary icon={<Gauge />} />
        <Metric label="Readiness" value={summary.readiness === "pass" ? "Pass" : "Fail"} caption="Non-compensating gates" icon={<ShieldAlert />} />
        <Metric label="Task success" value={formatPercent(summary.task_success_rate)} caption="Wilson 95% interval" icon={<CheckCircle2 />} />
        <Metric label="Strict pass³" value={formatPercent(summary.pass_power_k["3"])} caption="All 3 trials succeed" icon={<Sparkles />} />
        <Metric label="p95 latency" value={formatDuration(summary.latency_p95_ms)} caption={`p50 ${formatDuration(summary.latency_p50_ms)}`} icon={<Clock3 />} />
        <Metric label="Cost / success" value={formatCurrency(summary.cost_per_success_usd)} caption="Fixture agent · no API spend" icon={<CircleDollarSign />} />
      </section>
      <div className="chart-grid">
        <section className="panel"><PanelHead title="Category profile" subtitle="Balanced v1 weighting. Intervals are preserved with the stored observations." action={<Link href={`/runs/${run.run_id}`} className="ghost-button">Inspect evidence <ArrowRight size={14} /></Link>} /><CategoryChart categories={summary.categories} /><CategoryTable run={run} /></section>
        <section className="panel"><PanelHead title="Reliability signature" subtitle="pass@k reveals recoverability; strict passᵏ reveals consistency." /><ReliabilityChart run={run} /><table className="data-table sr-table"><caption className="sr-only">Reliability values</caption><thead><tr><th>k</th><th>pass@k</th><th>strict passᵏ</th></tr></thead><tbody>{Object.keys(summary.pass_at_k).map((k) => <tr key={k}><td>{k}</td><td>{formatPercent(summary.pass_at_k[k])}</td><td>{formatPercent(summary.pass_power_k[k])}</td></tr>)}</tbody></table></section>
      </div>
      <div className="chart-grid equal">
        <section className="panel"><PanelHead title="Task performance" subtitle="Base, perturbed, and ablated variants expose brittle success." /><HeatmapChart /></section>
        <section className="panel"><PanelHead title="Quality–latency frontier" subtitle="Compare operational tradeoffs without collapsing them into one number." /><ParetoChart runs={runs} /><div className="table-wrap"><table className="data-table"><caption className="sr-only">Quality and latency comparison</caption><thead><tr><th>Agent</th><th>Quality</th><th>p50 latency</th><th>Gate</th></tr></thead><tbody>{runs.map((item) => <tr key={item.run_id}><td><strong>{item.agent?.name}</strong></td><td>{item.summary?.quality_index ?? "—"}</td><td>{formatDuration(item.summary?.latency_p50_ms ?? 0)}</td><td><span className={`badge ${item.summary?.readiness === "pass" ? "good" : "warn"}`}>{item.summary?.readiness}</span></td></tr>)}</tbody></table></div></section>
      </div>
    </div>
  );
}

function Metric({ label, value, caption, primary, icon }: { label: string; value: string; caption: string; primary?: boolean; icon: React.ReactNode }) {
  return <article className={`metric-card ${primary ? "primary" : ""}`}><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-caption">{icon}{caption}</div></article>;
}
function PanelHead({ title, subtitle, action }: { title: string; subtitle: string; action?: React.ReactNode }) {
  return <div className="panel-head"><div><h2>{title}</h2><div className="panel-subtitle">{subtitle}</div></div>{action}</div>;
}
function CategoryTable({ run }: { run: Run }) {
  return <div className="table-wrap"><table className="data-table"><caption className="sr-only">Category scores with uncertainty</caption><thead><tr><th>Dimension</th><th>Score</th><th>95% interval</th><th>Weight</th><th>Evidence</th></tr></thead><tbody>{run.summary!.categories.map((row) => <tr key={row.category}><td><strong>{row.category}</strong></td><td><div style={{ display: "flex", alignItems: "center", gap: 9 }}><span>{row.score.toFixed(1)}</span><span className="score-bar"><span style={{ width: `${row.score}%` }} /></span></div></td><td>{row.interval ? `${row.interval.low.toFixed(1)}–${row.interval.high.toFixed(1)}` : "—"}</td><td>{formatPercent(row.weight)}</td><td>{row.observations}</td></tr>)}</tbody></table></div>;
}
