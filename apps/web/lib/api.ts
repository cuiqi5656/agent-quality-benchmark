import { demoRuns, fallbackAgents, fallbackSuites } from "./demo-data";
import type { Agent, Run, Suite } from "./types";

const apiPath = process.env.NEXT_PUBLIC_AQB_API_PATH ?? "/api/aqb";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const serverBase = process.env.AQB_API_INTERNAL_URL;
  const target = typeof window === "undefined"
    ? serverBase ? `${serverBase.replace(/\/$/, "")}/api${path}` : null
    : `${apiPath}${path}`;
  if (!target) throw new Error("AQB API is not configured for server rendering");
  const response = await fetch(target, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  if (!response.ok) throw new Error((await response.text()) || `Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export async function getRuns(): Promise<Run[]> {
  try { const runs = await request<Run[]>("/v1/runs"); return runs.length ? runs : demoRuns; } catch { return demoRuns; }
}
export async function getRun(id: string): Promise<Run> {
  const demo = demoRuns.find((run) => run.run_id === id);
  if (demo) return demo;
  return request<Run>(`/v1/runs/${encodeURIComponent(id)}`);
}
export async function getAgents(): Promise<Agent[]> {
  try { return await request<Agent[]>("/v1/agents"); } catch { return fallbackAgents; }
}
export async function getSuites(): Promise<Suite[]> {
  try { return await request<Suite[]>("/v1/suites"); } catch { return fallbackSuites; }
}
export async function createRun(payload: { agent_id: string; suite_id: string; repetitions: number; enable_model_judge: boolean; seed: number }) {
  return request<Run>("/v1/runs", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(payload) });
}

export async function createAgent(payload: { name: string; adapter_type: string; endpoint?: string; model?: string; secret?: string }) {
  return request<Agent>("/v1/agents", { method: "POST", body: JSON.stringify(payload) });
}

export async function uploadTrace(file: File) {
  const body = new FormData();
  body.set("file", file);
  const response = await fetch(`${apiPath}/v1/uploads/traces`, { method: "POST", body });
  if (!response.ok) throw new Error((await response.text()) || "Trace upload failed");
  return response.json() as Promise<{ artifact_id: string; run_id: string; protocol_version: string; trial_count: number }>;
}
