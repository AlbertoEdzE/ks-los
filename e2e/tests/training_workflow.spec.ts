import { test, expect } from '@playwright/test';

test.describe('ML Training Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();
    await page.getByRole('button', { name: 'ML Training' }).click();
  });

  test('Complete training lifecycle with mocked backend', async ({ page }) => {
    // Mock /training/plan
    await page.route('**/training/plan', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plan: {
            hyperparameters: { learning_rate: 0.1, max_depth: 5 },
            n_samples: 1000,
            notes: 'Mock plan'
          }
        })
      });
    });

    // Mock /training/execute
    await page.route('**/training/execute', async route => {
        // Simulate delay
        await new Promise(resolve => setTimeout(resolve, 500));
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                result: {
                    accuracy: 0.95,
                    auc: 0.98,
                    model_uri: 'models:/credit_risk_model/1'
                }
            })
        });
    });
    
    // Mock /model/reload
    await page.route('**/model/reload', async route => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'reloaded' })
        });
    });
    
     // Mock /training/drift
    await page.route('**/training/drift', async route => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ report_endpoint: '/mock-report' })
        });
    });

    // Step 1: Planning
    await expect(page.getByText('Training Plan')).toBeVisible();
    await page.getByRole('textbox').fill('Test training run');
    await page.getByRole('button', { name: 'Generate Plan' }).click();

    // Step 2: Execution
    await expect(page.getByText('Review & Execute')).toBeVisible();
    // Use filter to be more specific and avoid strict mode violations
    await expect(page.locator('pre').filter({ hasText: 'hyperparameters' })).toBeVisible(); 
    await page.getByRole('button', { name: 'Execute Training' }).click();
    
    // Wait for completion
    await expect(page.getByText('Training Successful')).toBeVisible();

    // Step 3: Deployment
    await expect(page.getByText('Results & Deployment')).toBeVisible();
    
    // Handle dialog
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Deploy Model' }).click();
    
    // Run Drift Check
    await page.getByRole('button', { name: 'Run Drift Check' }).click();
    await expect(page.getByText('View Report')).toBeVisible();
  });
});
