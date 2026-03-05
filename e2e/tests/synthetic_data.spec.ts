import { test, expect } from '@playwright/test';

test('synthetic data generation works with new UI controls', async ({ page }) => {
  await page.goto('/');
  // Login
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();

  // Wait for Admin Panel
  await expect(page.getByText('Synthetic Data Control')).toBeVisible();

  // Select Territory
  await page.getByLabel('Territory').selectOption('ECCU');

  // Select Archetype
  await page.getByLabel('Archetype').selectOption('standard');

  // Verify Seed input and tooltip
  const seedInput = page.getByLabel('Seed (optional) ℹ️');
  await expect(seedInput).toBeVisible();
  await expect(seedInput).toHaveAttribute('title', 'Enter a numeric seed for reproducibility');
  await seedInput.fill('12345');
  
  // Set count
  await page.getByLabel('Count').fill('100');

  // Start Generation
  await page.getByRole('button', { name: 'Start Generation' }).click();

  // Wait for completion (timeout 10s should be enough for 100 records)
  await expect(page.getByText('Status: completed', { exact: false })).toBeVisible({ timeout: 15000 });
  
  // Verify Validate Output button works
  await page.getByRole('button', { name: 'Validate Output' }).click();
  // Expect some JSON output in the message or at least not "Validation failed"
  // The validate output usually contains "approval_rate"
  await expect(page.getByText('approval_rate', { exact: false })).toBeVisible();
});
