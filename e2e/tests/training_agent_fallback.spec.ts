
import { test, expect } from '@playwright/test';

test.describe('Training Agent Fallback', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Check if we need to login
    try {
        await page.getByLabel('Username').waitFor({ state: 'visible', timeout: 3000 });
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin123');
        await page.getByRole('button', { name: 'Login' }).click();
    } catch (e) {
        // Already logged in
    }
    // Navigate to ML Training if not already there
    await page.getByRole('button', { name: 'ML Training' }).click();
    await page.getByRole('button', { name: 'Training Workflow' }).click();
  });

  test('should display fallback plan when LLM is unavailable', async ({ page }) => {
    // Mock the backend response to simulate fallback behavior
    // This matches what the backend now returns on LLM failure
    const fallbackPlan = {
        hyperparameters: {
            learning_rate: 0.1,
            max_depth: 5,
            n_estimators: 100,
            objective: "binary:logistic"
        },
        n_samples: 2000,
        notes: "Generated via fallback logic (LLM unavailable). Standard XGBoost configuration."
    };

    await page.route('**/training/plan', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ plan: fallbackPlan })
      });
    });

    // Trigger plan generation
    await expect(page.getByRole('button', { name: 'Generate Training Plan' })).toBeVisible();
    await page.getByRole('button', { name: 'Generate Training Plan' }).click();

    // Verify the fallback plan is displayed
    await expect(page.getByText('Proposed Plan')).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: 'Approve & Start Training' })).toBeVisible();
  });
});
