import { defineConfig, devices } from "@playwright/test";

/**
 * E2E runs against a real stack (`make up && make seed`): real browser, real API, real
 * PostgreSQL. It covers the single most important journey; everything else is cheaper to
 * test lower in the pyramid (docs/engineering-standards.md).
 */
export default defineConfig({
  testDir: "./e2e",
  // The journeys share one database and the same demo users, so they run one at a time.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
