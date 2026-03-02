import { test, expect } from '@playwright/test';

test('admin login shows AdminPanel and synthetic controls', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByLabel('Admin').check();
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByText('Synthetic Data Control')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Generation' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Validate Output' })).toBeVisible();
});
