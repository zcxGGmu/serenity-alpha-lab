import { defineConfig, devices } from '@playwright/test';

const browserUse = process.env.CI
  ? { ...devices['Desktop Chrome'] }
  : { ...devices['Desktop Chrome'], channel: 'msedge' };

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL: 'http://127.0.0.1:4175',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4175',
    url: 'http://127.0.0.1:4175',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: process.env.CI ? 'chromium' : 'msedge',
      use: browserUse,
    },
  ],
});
