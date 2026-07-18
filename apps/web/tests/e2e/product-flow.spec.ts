import { expect, test } from "@playwright/test";
import path from "node:path";

test("dashboard exposes key metrics and accessible chart tables", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Agent quality, made legible." })).toBeVisible();
  await expect(page.getByText("Quality Index").first()).toBeVisible();
  await expect(page.getByRole("table", { name: "Category scores with uncertainty" })).toBeAttached();
  await expect(page.getByText("Atlas").first()).toBeVisible();
  await page.screenshot({ path: path.resolve(process.cwd(), "../../docs/screenshots/dashboard.png"), fullPage: true });
});

test("guided setup and evidence explorer are navigable by role", async ({ page }) => {
  await page.goto("/runs/new");
  await expect(page.getByRole("heading", { name: "Start a benchmark" })).toBeVisible();
  await page.getByRole("button", { name: "AQB HTTP" }).click();
  await expect(page.getByLabel("HTTPS endpoint")).toBeVisible();
  await page.goto("/runs/demo-atlas-20260718");
  await expect(page.getByRole("heading", { name: "Atlas" })).toBeVisible();
  await page.getByRole("tab", { name: "Trace waterfall" }).click();
  await expect(page.getByRole("heading", { name: "Execution waterfall" })).toBeVisible();
  await page.getByRole("tab", { name: "Ablations" }).click();
  await expect(page.getByRole("cell", { name: "No demonstrated difference" })).toBeVisible();
  await page.screenshot({ path: path.resolve(process.cwd(), "../../docs/screenshots/run-explorer.png"), fullPage: true });
});

test("comparison communicates statistical non-differences", async ({ page }) => {
  await page.goto("/compare");
  await expect(page.getByRole("heading", { name: "Compare runs" })).toBeVisible();
  await expect(page.getByText("no demonstrated difference", { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: path.resolve(process.cwd(), "../../docs/screenshots/comparison.png"), fullPage: true });
});

test("mobile navigation and dark theme remain operable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  await page.getByRole("link", { name: "Compare" }).click();
  await expect(page.getByRole("heading", { name: "Compare runs" })).toBeVisible();
});
