export function percent(value: number, digits = 0): string {
  return new Intl.NumberFormat("en", { style: "percent", maximumFractionDigits: digits }).format(value);
}

export function compactNumber(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function latency(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${Math.round(value)}ms`;
}

export function money(value: number | null): string {
  return value === null ? "—" : new Intl.NumberFormat("en", { style: "currency", currency: "USD", maximumFractionDigits: 3 }).format(value);
}

export function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

export function clampScore(value: number): number {
  return Math.max(0, Math.min(100, value));
}

export const formatPercent = percent;
export const formatDuration = latency;
export const formatCurrency = money;
