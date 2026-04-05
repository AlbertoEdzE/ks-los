import { test, expect } from '@playwright/test';

async function ensureLoggedInIfPrompted(page: any) {
  try {
    await page.getByLabel('Username').waitFor({ state: 'visible', timeout: 800 });
    await page.getByLabel('Username').fill('officer');
    await page.getByLabel('Password').fill('Password123!');
    await page.getByRole('button', { name: 'Sign In' }).click();
  } catch {
    // already logged in
  }
}

test('officer hold page loads without breaking borrower flows', async ({ page }) => {
  await page.goto('/officer-hold', { waitUntil: 'domcontentloaded' });
  await ensureLoggedInIfPrompted(page);
  await page.waitForLoadState('networkidle');

  await expect(page.getByRole('heading', { name: 'Officer Hold' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Lead holds' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Loan holds' })).toBeVisible();
});

test('agentic console page loads', async ({ page }) => {
  await page.goto('/agentic-console', { waitUntil: 'domcontentloaded' });
  await ensureLoggedInIfPrompted(page);
  await page.waitForLoadState('networkidle');

  await expect(page.getByRole('heading', { name: 'Agentic Console' })).toBeVisible();
});
