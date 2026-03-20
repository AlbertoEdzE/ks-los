import { test, expect } from '@playwright/test';

test('admin login renders synthetic controls', async ({ page }) => {
  await page.goto('/dashboard');
  await page.getByLabel('Username').fill('officer');
  await page.getByLabel('Password').fill('Password123!');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.getByRole('link', { name: 'Synthetic Data' }).click();
  await expect(page.getByText('Synthetic Data Generator')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Generation' })).toBeVisible();
});
