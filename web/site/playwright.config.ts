import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  use: { baseURL: "http://127.0.0.1:4173", browserName: "chromium" },
  webServer: {
    command: "node test-server.mjs 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 10_000
  },
  outputDir: "../test-results"
});
