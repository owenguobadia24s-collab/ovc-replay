import { defineConfig } from "@playwright/test";
import path from "node:path";

const python = process.env.RCN_PYTHON ?? "python";

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR ?? path.resolve(process.cwd(), `../../artifacts/research_console_vnext/wp3e_convergence/playwright-results-${process.pid}`),
  timeout: 45_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:5173", colorScheme: "dark", trace: "retain-on-failure" },
  webServer: process.env.RCN_EXTERNAL_SERVERS ? undefined : [
    { command: `${python} -m apps.research_api`, cwd: "../..", env: { ...process.env, PYTHONPATH: ["src", "."].join(path.delimiter) }, url: "http://127.0.0.1:8765/api/v1/identity", reuseExistingServer: !process.env.CI, timeout: 120_000 },
    { command: "npm run dev", cwd: ".", url: "http://127.0.0.1:5173", reuseExistingServer: !process.env.CI, timeout: 120_000 },
  ],
});
