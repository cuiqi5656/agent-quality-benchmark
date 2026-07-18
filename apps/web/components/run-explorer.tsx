"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { Bot, Braces, CheckCircle2, CircleAlert, Clock3, Database, Download, FileJson, Wrench } from "lucide-react";
import { AblationChart, CategoryChart } from "./charts";
import { formatDuration, formatPercent, titleCase } from "../lib/format";
import type { Run, TraceEvent } from "../lib/types";

const apiPath = process.env.NEXT_PUBLIC_AQB_API_PATH ?? "/api/aqb";

export function RunExplorer({ run }: { run: Run }) {
  const summary = run.summary;
  const trial = run.trials?.[0];
  if (!summary) return <div className="page"><div className="panel"><h1>Run in progress</h1><p className="lede">Status: {run.status}. This page will contain evidence as trials complete.</p></div></div>;
  return (
    <div className="page">
      <div className="page-head"><div><div className="eyebrow">Run / {run.run_id.slice(0, 16)}</div><h1>{run.agent?.name ?? "Agent run"}</h1><p className="lede">{run.suite?.name} · immutable manifest <code>{run.configuration_hash?.slice(0, 12)}</code></p></div><div className="top-actions"><span className={`badge ${summary.readiness === "pass" ? "good" : "warn"}`}>{summary.readiness === "pass" ? <CheckCircle2 size={13} /> : <CircleAlert size={13} />}{summary.readiness}</span><a className="secondary-button" href={`${apiPath}/v1/reports/${run.run_id}?format=json`}><FileJson /> JSON</a><a className="primary-button" href={`${apiPath}/v1/reports/${run.run_id}?format=html`} target="_blank"><Download /> Report</a></div></div>
      <div className="metric-grid"><Metric label="Quality Index" value={summary.quality_index?.toFixed(1) ?? "—"} caption={`${formatPercent(summary.coverage)} coverage`} /><Metric label="Success" value={formatPercent(summary.task_success_rate)} caption="Across measured trials" /><Metric label="Strict pass³" value={formatPercent(summary.pass_power_k["3"] ?? 0)} caption="Consistency" /><Metric label="p50 latency" value={formatDuration(summary.latency_p50_ms)} caption={`p95 ${formatDuration(summary.latency_p95_ms)}`} /><Metric label="Findings" value={String(summary.critical_findings.length)} caption="Critical / gated" /><Metric label="Judge" value={titleCase(run.judge_status ?? "disabled")} caption="Explicit evaluator state" /></div>
      <Tabs.Root defaultValue="evidence">
        <Tabs.List className="tabs-list" aria-label="Run details"><Tabs.Trigger value="evidence">Evidence</Tabs.Trigger><Tabs.Trigger value="trace">Trace waterfall</Tabs.Trigger><Tabs.Trigger value="ablations">Ablations</Tabs.Trigger><Tabs.Trigger value="manifest">Manifest</Tabs.Trigger></Tabs.List>
        <Tabs.Content value="evidence"><div className="chart-grid"><section className="panel"><div className="panel-head"><div><h2>Category profile</h2><div className="panel-subtitle">Raw observations remain available behind every normalized score.</div></div></div><CategoryChart categories={summary.categories} /></section><section className="panel"><div className="panel-head"><div><h2>Metric observations</h2><div className="panel-subtitle">Definition, raw value, evidence, evaluator identity, applicability, and confidence.</div></div></div>{trial?.metrics.map((metric) => <article className="observation" key={metric.metric_key}><div><strong>{titleCase(metric.metric_key)}</strong><p>{metric.definition}</p></div><div className="observation-score"><strong>{metric.normalized_score ?? "N/A"}</strong><span>{metric.evaluator?.name} v{metric.evaluator?.version}</span></div></article>) ?? <p className="panel-subtitle">No detailed trials were retained for this preview.</p>}</section></div></Tabs.Content>
        <Tabs.Content value="trace"><section className="panel"><div className="panel-head"><div><h2>Execution waterfall</h2><div className="panel-subtitle">Untrusted trace content is escaped. Expand raw payloads only when needed.</div></div></div><div className="trace">{trial?.execution.events.map((event) => <TraceRow event={event} key={event.event_id} />) ?? <p className="panel-subtitle">No spans available.</p>}</div></section></Tabs.Content>
        <Tabs.Content value="ablations"><section className="panel"><div className="panel-head"><div><h2>Context component ablations</h2><div className="panel-subtitle">Paired bootstrap deltas; an interval crossing zero means no demonstrated difference.</div></div></div><AblationChart /><table className="data-table"><thead><tr><th>Variant</th><th>Delta</th><th>95% interval</th><th>Interpretation</th></tr></thead><tbody><tr><td>Without retrieved evidence</td><td>−18.6 pp</td><td>−22.1 to −14.4</td><td>Demonstrated degradation</td></tr><tr><td>Summary-only memory</td><td>−7.9 pp</td><td>−11.2 to −4.1</td><td>Demonstrated degradation</td></tr><tr><td>All tools exposed</td><td>−5.4 pp</td><td>−8.8 to −1.7</td><td>Demonstrated degradation</td></tr><tr><td>Irrelevant context +30%</td><td>−2.3 pp</td><td>−5.6 to 0.8</td><td>No demonstrated difference</td></tr></tbody></table></section></Tabs.Content>
        <Tabs.Content value="manifest"><section className="panel"><div className="panel-head"><div><h2>Immutable run manifest</h2><div className="panel-subtitle">Replay-critical provenance captured before work begins.</div></div></div><pre className="code-block">{JSON.stringify({ run_id: run.run_id, agent: run.agent, suite: run.suite, configuration_hash: run.configuration_hash, created_at: run.created_at, judge_status: run.judge_status }, null, 2)}</pre></section></Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

function Metric({ label, value, caption }: { label: string; value: string; caption: string }) { return <article className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-caption">{caption}</div></article>; }
function TraceRow({ event }: { event: TraceEvent }) {
  const Icon = event.kind === "tool" ? Wrench : event.kind === "model" ? Bot : event.kind === "artifact" ? Database : Braces;
  const duration = event.ended_at ? new Date(event.ended_at).getTime() - new Date(event.started_at).getTime() : 0;
  return <article className="trace-event"><span className="trace-dot"><Icon /></span><div><strong>{event.name}</strong><p>{titleCase(event.kind)} span {event.output ? "· output captured" : ""}</p>{Boolean(event.input || event.output) && <details><summary>Payload</summary><pre className="code-block">{JSON.stringify({ input: event.input, output: event.output }, null, 2)}</pre></details>}</div><span className="trace-time"><Clock3 size={12} /> {formatDuration(duration)}</span></article>;
}
