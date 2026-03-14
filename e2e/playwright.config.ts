import { defineConfig, devices } from '@playwright/test';
const env = (globalThis as unknown as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!env.CI,
  retries: env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],
  timeout: 120 * 1000,
  use: {
    baseURL: env.BASE_URL || 'http://localhost:5174',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        launchOptions: {
          env: {
            MOZ_DISABLE_CONTENT_SANDBOX: '1',
            MOZ_DISABLE_GMP_SANDBOX: '1',
            MOZ_DISABLE_RDD_SANDBOX: '1',
          },
        },
      },
    },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
