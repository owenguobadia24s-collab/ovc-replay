import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:5173", colorScheme: "dark", trace: "retain-on-failure" },
  webServer: [
    { command: "cd ../.. && PYTHONPATH=src:. python -m apps.research_api", url: "http://127.0.0.1:8765/api/v1/identity", reuseExistingServer: !process.env.CI, timeout: 120_000 },
    { command: "npm run dev", url: "http://127.0.0.1:5173", reuseExistingServer: !process.env.CI, timeout: 120_000 },
  ],
});
