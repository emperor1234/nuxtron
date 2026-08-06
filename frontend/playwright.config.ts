import { defineConfig, devices } from '@playwright/test';

const frontendPort = 4273;
const mockApiPort = 4101;

export default defineConfig({
  testDir: './tests/smoke',
  reporter: 'line',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: `http://localhost:${frontendPort}`,
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'node tests/mock-fastapi-server.js',
      cwd: __dirname,
      url: `http://localhost:${mockApiPort}/healthz`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `npx next dev --webpack -p ${frontendPort} --hostname localhost`,
      cwd: __dirname,
      url: `http://localhost:${frontendPort}/api/health`,
      reuseExistingServer: true,
      timeout: 300_000,
      env: {
        CI: '1',
        NEXT_PUBLIC_FASTAPI_URL: `http://localhost:${mockApiPort}`,
        FASTAPI_URL: `http://localhost:${mockApiPort}`,
        NEXT_PUBLIC_FASTAPI_API_KEY: 'change-this-fastapi-key',
        FASTAPI_API_KEY: 'change-this-fastapi-key',
        NEXT_PUBLIC_DEFAULT_TENANT_ID: 'tenant-demo',
        NEXT_PUBLIC_DISABLE_WEB_VITALS_BUDGET: '1',
        // The smoke suite navigates straight to protected routes with no
        // login step. proxy.ts and ClientAuthGuard both honor this same
        // flag — must never be set outside test/dev.
        NEXT_PUBLIC_DISABLE_AUTH_GUARD: 'true',
        DEFAULT_TENANT_ID: 'tenant-demo',
        DJANGO_API_URL: `http://localhost:${mockApiPort}/django/health`,
      },
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
});
