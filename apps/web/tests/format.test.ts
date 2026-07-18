import { clampScore, formatCurrency, formatDuration, formatPercent, titleCase } from "../lib/format";

describe("metric formatting", () => {
  it("keeps units and missing values explicit", () => {
    expect(formatPercent(0.944)).toBe("94%");
    expect(formatDuration(842)).toBe("842ms");
    expect(formatDuration(1870)).toBe("1.9s");
    expect(formatCurrency(null)).toBe("—");
  });

  it("clamps normalized scores and humanizes protocol keys", () => {
    expect(clampScore(120)).toBe(100);
    expect(clampScore(-1)).toBe(0);
    expect(titleCase("strict_pass_k")).toBe("Strict Pass K");
  });
});
