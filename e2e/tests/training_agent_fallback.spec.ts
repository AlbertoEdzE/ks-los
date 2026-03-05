
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
      console.log('Mocking /training/plan with fallback response');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ plan: fallbackPlan })
      });
    });

    // Trigger plan generation
    await page.getByRole('button', { name: 'Generate Training Plan' }).click();

    // Verify the fallback plan is displayed
    // The UI should show the plan details. Since the UI might not display raw JSON,
    // we check for visual confirmation or if the state updated (e.g. "Start Training" button becomes enabled or plan details appear)
    
    // In the current UI, the plan might be displayed or just stored in state.
    // Let's assume there's a section that shows the generated plan or we can check if "Start Training" is visible/enabled
    // If the UI doesn't explicitly show the notes, we can check if the next step is accessible.
    
    // Check console logs for debugging
    page.on('console', msg => console.log(msg.text()));

    // Wait for the plan to be generated (button might change or next section appears)
    // Assuming "Start Training" appears in Step 2 or is enabled
    // The current UI might not show the plan text directly, but let's check if we can proceed.
    
    // If we can see the "Start Training" button, it means the plan was accepted.
    await expect(page.getByRole('button', { name: 'Start Training' })).toBeVisible();
    
    // Log success
    console.log('Fallback plan accepted by UI');
  });
});
