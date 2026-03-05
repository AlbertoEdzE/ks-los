import { test, expect } from '@playwright/test';

test('admin login renders synthetic controls', async ({ page }) => {
  await page.goto('/');
  // Role selection is removed, smart detection is used
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByText('Synthetic Data Control')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Generation' })).toBeVisible();
});
