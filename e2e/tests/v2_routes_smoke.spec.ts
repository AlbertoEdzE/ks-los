import { test, expect } from '@playwright/test';

test.describe('V2 Route Skeleton', () => {
  test('Officer routes render and navigate', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Pipeline' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Loan Products' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Officer Chat' })).toBeVisible();

    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

    await page.getByRole('link', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();

    await page.getByRole('link', { name: 'Loan Products' }).click();
    await expect(page.getByTestId('heading-loan-products')).toBeVisible();

    await page.getByRole('link', { name: 'Officer Chat' }).click();
    await expect(page.getByTestId('heading-officer-chat')).toBeVisible();
  });

  test('Borrower route renders after login', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Username').fill('demo');
    await page.getByLabel('Password').fill('demo123');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByRole('heading', { name: 'Loan Navigator' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Logout' })).toBeVisible();
  });
});

