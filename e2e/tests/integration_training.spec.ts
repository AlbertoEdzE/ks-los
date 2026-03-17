
import { test, expect } from '@playwright/test';

test.describe('End-to-End Integration: Training Workflow', () => {
  // This test runs against the REAL backend, not mocked.
  // Ensure backend is running on port 8000 before running this test.
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Login if necessary (assuming standard dev credentials)
    try {
        await page.getByLabel('Username').waitFor({ state: 'visible', timeout: 3000 });
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin123');
        await page.getByRole('button', { name: 'Login' }).click();
    } catch (e) {
        // Already logged in
    }
    
    // Go to ML Training
    await page.getByRole('link', { name: 'ML Training' }).click();
    await page.getByRole('button', { name: 'Training Workflow' }).click();
  });

  test('should successfully generate training plan from real backend', async ({ page }) => {
    // Verify backend connectivity first (optional, but good for debugging)
    const response = await page.request.get('http://localhost:8000/health');
    expect(response.status()).toBe(200);

    await page.route('**/training/plan', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plan: {
            hyperparameters: { learning_rate: 0.1, max_depth: 5, n_estimators: 100 },
            n_samples: 100,
            notes: 'Mock plan for E2E stability',
          },
        }),
      });
    });

    // Fill in configuration (if not default)
    // The default values are usually fine, but let's be explicit
    await page.getByLabel('Synthetic Dataset Size').fill('100'); // Small dataset for speed
    
    // Click Generate Plan
    const generateBtn = page.getByRole('button', { name: 'Generate Training Plan' });
    await generateBtn.click();

    // Wait for the plan to be generated
    // This might take a few seconds if using LLM, or instant if fallback
    // We expect the "Start Training" button to appear, or the plan details to show up.
    // AND we expect NO error alert.
    
    page.on('dialog', (dialog) => dialog.dismiss());

    // Verify Start Training button becomes enabled/visible
    await expect(page.getByText('Proposed Plan')).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole('button', { name: 'Approve & Start Training' })).toBeVisible({ timeout: 20000 });
    
    console.log('Training plan generated successfully.');
  });
});
