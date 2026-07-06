const { defineConfig, devices } = require("@playwright/test");

const baseURL = process.env.BANK_STATEMENT_E2E_BASE_URL || "http://127.0.0.1:8501";
const defaultPython = process.platform === "win32" ? "venv\\Scripts\\python.exe" : "python";
const serverCommand =
  process.env.BANK_STATEMENT_E2E_SERVER_CMD || `${defaultPython} scripts/run_app.py --mode production-test`;

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: {
    timeout: 20_000,
  },
  reporter: process.env.CI ? [["list"]] : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: serverCommand,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
