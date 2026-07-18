import { Dashboard } from "../components/dashboard";
import { getRuns } from "../lib/api";

export default async function HomePage() {
  return <Dashboard runs={await getRuns()} />;
}
