import { test, expect } from '@playwright/test';

test('synthetic data generation works with new UI controls', async ({ page }) => {
  await page.route('http://localhost:8000/admin/synthetic/generate', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    await route.fulfill({ status: 200, body: '' });
  });

  await page.route('http://localhost:8000/admin/synthetic/stream', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'content-type': 'text/event-stream',
        'cache-control': 'no-cache',
        connection: 'keep-alive',
      },
      body: "data: {'progress':100,'status':'completed','message':'done'}\n\n",
    });
  });

  await page.route('http://localhost:8000/admin/synthetic/validate', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ approval_rate: 0.42 }),
    });
  });

  await page.goto('/dashboard');
  // Login
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();

  // Wait for Admin Panel
  await page.getByRole('button', { name: 'Synthetic Data' }).click();
  await expect(page.getByText('Synthetic Data Generator')).toBeVisible();

  // Select Territory
  await page.getByLabel('Territory').selectOption('ECCU');

  // Select Archetype
  await page.getByLabel('Archetype').selectOption('standard');

  // Verify Seed input and tooltip
  await expect(page.locator('span[title="Use a numeric seed for reproducible data generation"]')).toBeVisible();
  const seedInput = page.getByLabel('Seed (Optional)');
  await expect(seedInput).toBeVisible();
  await seedInput.fill('12345');
  
  // Set count
  await page.getByLabel('Count').fill('100');

  // Start Generation
  await page.getByRole('button', { name: 'Start Generation' }).click();

  // Wait for completion
  await expect(page.getByText(/completed/i)).toBeVisible({ timeout: 15000 });
  
  // Verify Validate Output button works
  await page.getByRole('button', { name: 'Validate Output' }).click();
  await expect(page.getByText('approval_rate', { exact: false })).toBeVisible({ timeout: 10000 });
});
