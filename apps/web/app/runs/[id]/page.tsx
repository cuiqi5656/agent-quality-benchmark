import { notFound } from "next/navigation";
import { RunExplorer } from "../../../components/run-explorer";
import { getRun } from "../../../lib/api";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let run;
  try { run = await getRun(id); } catch { notFound(); }
  return <RunExplorer run={run} />;
}
