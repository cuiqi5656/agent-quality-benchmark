import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: { baseURL: "http://127.0.0.1:3000", trace: "retain-on-failure" },
  webServer: { command: "node node_modules/next/dist/bin/next dev -H 127.0.0.1", url: "http://127.0.0.1:3000", reuseExistingServer: true, timeout: 120_000 },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }]
});
