import { NewRunWizard } from "../../../components/new-run-wizard";
import { getAgents, getSuites } from "../../../lib/api";

export const metadata = { title: "New benchmark" };

export default async function NewRunPage() {
  const [agents, suites] = await Promise.all([getAgents(), getSuites()]);
  return <NewRunWizard agents={agents} suites={suites} />;
}
