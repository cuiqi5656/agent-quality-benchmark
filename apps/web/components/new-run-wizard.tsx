"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Braces, ChevronLeft, ChevronRight, FileArchive, Globe2, ShieldCheck, UploadCloud } from "lucide-react";
import { createAgent, createRun, uploadTrace } from "../lib/api";
import type { Agent, Suite } from "../lib/types";

type Touchpoint = "existing" | "aqb_http" | "openai_compatible" | "trace_upload";

export function NewRunWizard({ agents: initialAgents, suites }: { agents: Agent[]; suites: Suite[] }) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [touchpoint, setTouchpoint] = useState<Touchpoint>("existing");
  const [agents, setAgents] = useState(initialAgents);
  const [agentId, setAgentId] = useState(initialAgents[0]?.id ?? "");
  const [suiteId, setSuiteId] = useState(suites[0]?.id ?? "");
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [model, setModel] = useState("");
  const [secret, setSecret] = useState("");
  const [repetitions, setRepetitions] = useState(3);
  const [judge, setJudge] = useState(false);
  const [upload, setUpload] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function continueFromAgent() {
    setError("");
    if (touchpoint === "trace_upload") {
      if (!upload) return setError("Choose a JSON, JSONL, or ZIP trace bundle first.");
      setBusy(true);
      try { const imported = await uploadTrace(upload); router.push(`/runs/${imported.run_id}`); } catch (reason) { setError(reason instanceof Error ? reason.message : "Upload failed"); setBusy(false); }
      return;
    }
    if (touchpoint !== "existing") {
      if (!name || !endpoint || (touchpoint === "openai_compatible" && !model)) return setError("Name, endpoint, and model where applicable are required.");
      setBusy(true);
      try {
        const agent = await createAgent({ name, endpoint, model: model || undefined, secret: secret || undefined, adapter_type: touchpoint });
        setAgents((current) => [...current, agent]); setAgentId(agent.id); setStep(1);
      } catch (reason) { setError(reason instanceof Error ? reason.message : "Connection failed"); } finally { setBusy(false); }
      return;
    }
    if (!agentId) return setError("Select an agent.");
    setStep(1);
  }

  async function startRun() {
    if (!agentId || !suiteId) return setError("Select an agent and benchmark suite.");
    setBusy(true); setError("");
    try { const run = await createRun({ agent_id: agentId, suite_id: suiteId, repetitions, enable_model_judge: judge, seed: 7 }); router.push(`/runs/${run.run_id}`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Run could not be started"); setBusy(false); }
  }

  return (
    <div className="page">
      <div className="page-head"><div><div className="eyebrow">Guided evaluation</div><h1>Start a benchmark</h1><p className="lede">Connect a live agent or import a portable trace, then select a versioned suite and an explicit evaluation policy.</p></div><span className="badge info"><ShieldCheck size={13} /> no uploaded code execution</span></div>
      <div className="panel form-panel">
        <div className="stepper" aria-label="Benchmark setup progress">{["Touchpoint", "Suite", "Evaluation", "Review"].map((label, index) => <div className={`step ${index === step ? "active" : index < step ? "done" : ""}`} key={label} aria-current={index === step ? "step" : undefined}>{label}</div>)}</div>
        {step === 0 && <>
          <div className="panel-head"><div><h2>How should AQB observe this agent?</h2><div className="panel-subtitle">Live adapters execute fixture tasks; trace import evaluates work that already happened.</div></div></div>
          <div className="choice-grid">
            <Choice selected={touchpoint === "existing"} onClick={() => setTouchpoint("existing")} icon={<Bot />} title="Saved agent" text="Use a configured demo or live endpoint." />
            <Choice selected={touchpoint === "aqb_http"} onClick={() => setTouchpoint("aqb_http")} icon={<Braces />} title="AQB HTTP" text="Synchronous output, events, usage, and status contract." />
            <Choice selected={touchpoint === "openai_compatible"} onClick={() => setTouchpoint("openai_compatible")} icon={<Globe2 />} title="OpenAI-compatible" text="Run through AQB’s versioned fixture-tool loop." />
            <Choice selected={touchpoint === "trace_upload"} onClick={() => setTouchpoint("trace_upload")} icon={<FileArchive />} title="Trace upload" text="Validate JSON, JSONL, or a safe ZIP bundle." />
          </div>
          <div style={{ height: 20 }} />
          {touchpoint === "existing" && <div className="field"><label htmlFor="agent">Agent</label><select id="agent" className="select" value={agentId} onChange={(event) => setAgentId(event.target.value)}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name} · {agent.adapter_type}</option>)}</select></div>}
          {(touchpoint === "aqb_http" || touchpoint === "openai_compatible") && <div className="field-grid">
            <div className="field"><label htmlFor="name">Display name</label><input className="input" id="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="My agent v3" /></div>
            <div className="field"><label htmlFor="endpoint">HTTPS endpoint</label><input className="input" id="endpoint" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} placeholder="https://agent.example.com/v1" /></div>
            {touchpoint === "openai_compatible" && <div className="field"><label htmlFor="model">Model identifier</label><input className="input" id="model" value={model} onChange={(event) => setModel(event.target.value)} placeholder="agent-model" /></div>}
            <div className="field"><label htmlFor="secret">Bearer credential</label><input className="input" id="secret" value={secret} onChange={(event) => setSecret(event.target.value)} placeholder="Stored encrypted; never returned" type="password" autoComplete="new-password" /></div>
          </div>}
          {touchpoint === "trace_upload" && <div className="upload-zone"><UploadCloud /><label htmlFor="trace-file"><strong>Choose a trace bundle</strong><span>{upload?.name ?? "JSON, JSONL, or ZIP · max 25 MB"}</span></label><input id="trace-file" type="file" accept=".json,.jsonl,.zip,application/json,application/zip" onChange={(event) => setUpload(event.target.files?.[0] ?? null)} /></div>}
        </>}
        {step === 1 && <><div className="panel-head"><div><h2>Choose a benchmark suite</h2><div className="panel-subtitle">Every suite is immutable by version and records its provenance.</div></div></div><div className="pack-grid">{suites.map((suite) => <button key={suite.id} className={`choice-card ${suiteId === suite.id ? "selected" : ""}`} onClick={() => setSuiteId(suite.id)}><div className="pack-top"><span className="choice-icon"><Braces /></span><span className="badge neutral">v{suite.version}</span></div><h3>{suite.name}</h3><p>{suite.case_count} deterministic cases with perturbation and ablation variants.</p></button>)}</div></>}
        {step === 2 && <><div className="panel-head"><div><h2>Configure evaluation policy</h2><div className="panel-subtitle">Repetitions measure variance. The optional semantic judge stays explicitly unavailable until configured.</div></div></div><div className="field"><label htmlFor="repetitions">Repetitions per case</label><input className="input" id="repetitions" type="number" min={1} max={10} value={repetitions} onChange={(event) => setRepetitions(Number(event.target.value))} /></div><div className="switch-row"><div><strong>Semantic model judge</strong><div className="panel-subtitle">Strict Structured Outputs · configured model only · no silent substitution</div></div><button aria-pressed={judge} className={`switch ${judge ? "on" : ""}`} onClick={() => setJudge(!judge)}><span /></button></div><div className="switch-row"><div><strong>Static perturbations and ablations</strong><div className="panel-subtitle">Enabled by the selected suite manifest</div></div><span className="badge good">enabled</span></div></>}
        {step === 3 && <><div className="panel-head"><div><h2>Review immutable run manifest</h2><div className="panel-subtitle">The configuration hash, evaluator versions, seed, inputs, and target are captured before execution.</div></div></div><div className="review-grid"><div><span>Agent</span><strong>{agents.find((agent) => agent.id === agentId)?.name ?? "Imported trace"}</strong></div><div><span>Suite</span><strong>{suites.find((suite) => suite.id === suiteId)?.name}</strong></div><div><span>Repetitions</span><strong>{repetitions} × per case</strong></div><div><span>Model judge</span><strong>{judge ? "Requested (requires key)" : "Disabled"}</strong></div></div></>}
        {error && <div className="error-callout" role="alert">{error}</div>}
        <div className="form-actions"><button className="ghost-button" disabled={step === 0 || busy} onClick={() => setStep(Math.max(0, step - 1))}><ChevronLeft /> Back</button>{step === 0 ? <button className="primary-button" disabled={busy} onClick={continueFromAgent}>{busy ? "Validating…" : touchpoint === "trace_upload" ? "Import & evaluate" : "Continue"}<ChevronRight /></button> : step < 3 ? <button className="primary-button" onClick={() => setStep(step + 1)}>Continue <ChevronRight /></button> : <button className="primary-button" disabled={busy} onClick={startRun}>{busy ? "Queuing…" : "Start benchmark"}<ChevronRight /></button>}</div>
      </div>
    </div>
  );
}

function Choice({ selected, onClick, icon, title, text }: { selected: boolean; onClick: () => void; icon: React.ReactNode; title: string; text: string }) {
  return <button aria-pressed={selected} className={`choice-card ${selected ? "selected" : ""}`} onClick={onClick}><span className="choice-icon">{icon}</span><h3>{title}</h3><p>{text}</p></button>;
}
