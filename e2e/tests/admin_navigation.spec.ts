import { test, expect } from '@playwright/test';

test.describe('Admin Panel Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();
  });

  test('Sidebar navigation works', async ({ page }) => {
    // Check initial state
    await expect(page.getByRole('heading', { name: 'Synthetic Data Control' })).toBeVisible();

    // Click Configuration
    await page.getByRole('button', { name: 'Configuration' }).click();
    await expect(page.getByRole('heading', { name: 'Configuration' })).toBeVisible();

    // Click Model
    await page.getByRole('button', { name: 'Model' }).click();
    await expect(page.getByRole('heading', { name: 'Model' })).toBeVisible();

    // Click Metrics
    await page.getByRole('button', { name: 'Metrics' }).click();
    await expect(page.getByRole('heading', { name: 'Metrics' })).toBeVisible();

    // Click Training
    await page.getByRole('button', { name: 'ML Training' }).click();
    await expect(page.getByRole('heading', { name: 'ML Model Training Pipeline' })).toBeVisible();
  });

  test('Training tab shows steps', async ({ page }) => {
    await page.getByRole('button', { name: 'ML Training' }).click();
    
    // Check steps
    await expect(page.getByText('Planning')).toBeVisible();
    await expect(page.getByText('Execution')).toBeVisible();
    await expect(page.getByText('Deployment')).toBeVisible();

    // Check Planning content
    await expect(page.getByRole('heading', { name: 'Training Plan' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate Plan' })).toBeVisible();
  });
});
