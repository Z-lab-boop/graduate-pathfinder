import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  projects: [
    // Playwright greps the full project/file/title string, so title-only anchors miss.
    { name: "chromium", grepInvert: /JavaScript fallback/, use: { browserName: "chromium" } },
    { name: "no-javascript", grep: /JavaScript fallback/, use: { browserName: "chromium", javaScriptEnabled: false } }
  ],
  use: { baseURL: "http://127.0.0.1:4173", browserName: "chromium" },
  webServer: {
    command: "node test-server.mjs 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 10_000
  },
  outputDir: "../test-results"
});
