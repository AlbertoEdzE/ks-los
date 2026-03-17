import { test, expect } from '@playwright/test';

test('synthetic data generation works with new UI controls', async ({ page }) => {
  await page.goto('/dashboard');
  // Login
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();

  await page.getByRole('link', { name: 'Synthetic Data' }).click();
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
  await page.getByLabel('Count').fill('10');

  // Start Generation
  await page.getByRole('button', { name: 'Start Generation' }).click();

  // Wait for completion
  await expect(page.getByText(/completed/i)).toBeVisible({ timeout: 60000 });
  
  // Verify Validate Output button works
  await page.getByRole('button', { name: 'Validate Output' }).click();
  await expect(page.getByText('approval_rate', { exact: false })).toBeVisible({ timeout: 10000 });
});
