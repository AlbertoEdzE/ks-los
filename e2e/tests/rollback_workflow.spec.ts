import { test, expect } from '@playwright/test';

test.describe('Model Rollback Workflow', () => {
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

  test('should allow admin to rollback model', async ({ page }) => {
    // Mock Training Plan
    await page.route('**/training/plan', async route => {
      await route.fulfill({
        json: {
          plan: {
            hyperparameters: { learning_rate: 0.01 },
            n_samples: 2000,
            notes: 'Mock Plan'
          }
        }
      });
    });

    // Mock Training Execute
    await page.route('**/training/execute', async route => {
      await route.fulfill({
        status: 200,
        json: { status: 'started', task_id: '123' }
      });
    });

    // Mock Training Status to be completed immediately
    await page.route('**/training/status', async route => {
      await route.fulfill({
        json: {
          is_training: false,
          progress: 100,
          status: 'completed',
          logs: ['Done'],
          result: {
            accuracy: 0.95,
            auc: 0.98,
            precision: 0.94,
            recall: 0.96,
            f1: 0.95,
            confusion_matrix: [[100, 10], [5, 100]],
            model_uri: 'models:/credit_risk_model/2',
            run_id: 'run-123',
            dataset_size: 1000,
            train_size: 800,
            test_size: 200
          },
          duration: 10
        }
      });
    });

    // Mock Batch Test
    await page.route('**/training/test', async route => {
        await route.fulfill({
            json: {
                results: [
                    {
                        input: { credit_score: 720, total_debt: 5000 },
                        prediction: 0,
                        probability: 0.05,
                        risk_level: 'Low'
                    }
                ]
            }
        });
    });

    // Mock Deploy (Reload)
    await page.route('**/model/reload', async route => {
        await route.fulfill({
            status: 200,
            json: { status: 'reloaded', message: 'Model reloaded' }
        });
    });

    // Mock Rollback Endpoint
    await page.route('**/model/rollback', async route => {
      await route.fulfill({
        status: 200,
        json: {
          status: 'rolled_back',
          message: 'Rolled back to version 1',
          version: '1'
        }
      });
    });

    // Navigate to page (Already done in beforeEach)
    // await page.goto('/training');

    // Generate Plan first
    await page.getByRole('button', { name: 'Generate Training Plan' }).click();
    await expect(page.getByText('Proposed Plan')).toBeVisible();

    // Start Training
    await page.getByRole('button', { name: 'Approve & Start Training' }).click();

    // Step 2: Execution -> Proceed to Analysis
    // Since we mock status as completed, the "Proceed" button should appear
    await expect(page.getByRole('button', { name: 'Proceed to Analysis' })).toBeVisible();
    await page.getByRole('button', { name: 'Proceed to Analysis' }).click();

    // Step 3: Analysis -> Proceed to Testing
    await expect(page.getByRole('button', { name: 'Proceed to Testing' })).toBeVisible();
    await page.getByRole('button', { name: 'Proceed to Testing' }).click();

    // Step 4: Testing -> Proceed to Deployment
    await expect(page.getByRole('button', { name: 'Run Inference' })).toBeVisible();
    // We can skip running inference and just go to deployment if the button is there?
    // Wait, step 4 requires "Proceed to Deployment" button which is always there?
    // Let's check renderStep4 in TrainingPanel.tsx
    // Yes, the button is always rendered at the bottom.
    await expect(page.getByRole('button', { name: 'Proceed to Deployment' })).toBeVisible();
    await page.getByRole('button', { name: 'Proceed to Deployment' }).click();

    // Step 5: Deployment
    await expect(page.getByRole('heading', { name: 'Deployment' })).toBeVisible();
    
    // Verify Rollback Section
    await expect(page.getByRole('heading', { name: 'Emergency Rollback' })).toBeVisible();
    
    const rollbackBtn = page.getByRole('button', { name: 'Rollback to Previous Version' });
    await expect(rollbackBtn).toBeVisible();
    
    // Click Rollback
    await rollbackBtn.click();
    
    // Verify Success State
    await expect(page.getByText('Rolled back to version 1')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Rolled Back Successfully' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Rolled Back Successfully' })).toBeDisabled();
  });
});
