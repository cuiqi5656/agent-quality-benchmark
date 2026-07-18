import { CompareView } from "../../components/compare-view";
import { getRuns } from "../../lib/api";

export const metadata = { title: "Compare runs" };
export default async function ComparePage() { return <CompareView runs={await getRuns()} />; }
