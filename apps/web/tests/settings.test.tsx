import { render, screen } from "@testing-library/react";
import SettingsPage from "../app/settings/page";

describe("secure settings", () => {
  it("labels the deferred judge setup without hiding deterministic readiness", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: "Workspace settings" })).toBeInTheDocument();
    expect(screen.getAllByText("final setup TODO").length).toBeGreaterThan(0);
    expect(screen.getByDisplayValue("gpt-5.6-terra")).toBeInTheDocument();
    expect(screen.getByText("Artifact execution")).toBeInTheDocument();
  });
});
