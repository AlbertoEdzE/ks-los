import { test, expect } from '@playwright/test';

test('admin login renders synthetic controls', async ({ page }) => {
  await page.goto('/dashboard');
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.getByRole('button', { name: 'Synthetic Data' }).click();
  await expect(page.getByText('Synthetic Data Generator')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Generation' })).toBeVisible();
});
