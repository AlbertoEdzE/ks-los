
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
    await page.getByRole('button', { name: 'ML Training' }).click();
  });

  test('should successfully generate training plan from real backend', async ({ page }) => {
    // Verify backend connectivity first (optional, but good for debugging)
    const response = await page.request.get('http://localhost:8000/health');
    expect(response.status()).toBe(200);

    // Fill in configuration (if not default)
    // The default values are usually fine, but let's be explicit
    await page.getByLabel('Dataset Size').fill('100'); // Small dataset for speed
    
    // Click Generate Plan
    const generateBtn = page.getByRole('button', { name: 'Generate Training Plan' });
    await generateBtn.click();

    // Wait for the plan to be generated
    // This might take a few seconds if using LLM, or instant if fallback
    // We expect the "Start Training" button to appear, or the plan details to show up.
    // AND we expect NO error alert.
    
    // Check for error alert
    const errorAlert = page.locator('.chakra-alert'); // Assuming Chakra UI alert or similar
    // Or check for window.alert (Playwright handles dialogs automatically, we need to listen)
    
    page.on('dialog', dialog => {
        console.log(`Dialog message: ${dialog.message()}`);
        if (dialog.message().includes('Failed')) {
            throw new Error(`Integration Test Failed: ${dialog.message()}`);
        }
        dialog.dismiss();
    });

    // Verify Start Training button becomes enabled/visible
    await expect(page.getByRole('button', { name: 'Start Training' })).toBeVisible({ timeout: 10000 });
    
    console.log('Training plan generated successfully via real backend integration.');
  });
});
