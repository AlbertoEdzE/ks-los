import { test, expect } from '@playwright/test';

test.describe('ML Training Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByLabel('Username').fill('officer');
    await page.getByLabel('Password').fill('Password123!');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.getByRole('link', { name: 'ML Training' }).click();
    await page.getByRole('button', { name: 'Training Workflow' }).click();
  });

  test('Complete 5-step training lifecycle with mocked backend', async ({ page }) => {
    // --- Mocks ---

    // 1. Mock /training/plan
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

    // 2. Mock /training/execute
    await page.route('**/training/execute', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'started', message: 'Training started' })
      });
    });

    // 3. Mock /training/status (Sequence of responses)
    let statusCallCount = 0;
    await page.route('**/training/status', async route => {
      statusCallCount++;
      if (statusCallCount <= 1) {
        // First call: Running
        await route.fulfill({
          json: {
            is_training: true,
            progress: 50,
            status: 'training',
            logs: ['Starting...', 'Epoch 1/10'],
            result: null,
            error: null,
            duration: 5
          }
        });
      } else {
        // Second call: Completed
        await route.fulfill({
          json: {
            is_training: false,
            progress: 100,
            status: 'completed',
            logs: ['Starting...', 'Epoch 1/10', 'Done'],
            result: {
              accuracy: 0.95,
              auc: 0.98,
              precision: 0.94,
              recall: 0.96,
              f1: 0.95,
              confusion_matrix: [[450, 50], [40, 460]],
              model_uri: 'models:/credit_risk_model/1',
              run_id: 'mock-run-id',
              dataset_size: 1000,
              train_size: 800,
              test_size: 200
            },
            error: null,
            duration: 10
          }
        });
      }
    });

    // 4. Mock /training/test
    await page.route('**/training/test', async route => {
      await route.fulfill({
        json: {
          results: [
            {
              input: { credit_score: 720, total_debt: 5000 },
              prediction: 0,
              probability: 0.1,
              risk_level: 'Low'
            }
          ]
        }
      });
    });

    // 5. Mock /model/reload
    await page.route('**/model/reload', async route => {
      await route.fulfill({
        status: 200,
        json: { status: 'reloaded' }
      });
    });

    // --- Steps ---

    // Step 1: Configuration
    await expect(page.getByText('Configuration & Planning')).toBeVisible();
    await page.getByLabel('Rationale / Strategy').fill('E2E Test Rationale');
    await page.getByRole('button', { name: 'Generate Training Plan' }).click();

    // Verify Plan & Advance
    await expect(page.getByText('Proposed Plan')).toBeVisible();
    await expect(page.locator('pre').filter({ hasText: 'learning_rate' })).toBeVisible();
    await page.getByRole('button', { name: 'Approve & Start Training' }).click();

    // Step 2: Execution
    await expect(page.getByText('Training Execution')).toBeVisible();
    await expect(page.getByText('50%')).toBeVisible(); // From first status mock
    // Wait for completion (second status mock)
    await expect(page.getByRole('button', { name: 'Proceed to Analysis' })).toBeVisible({ timeout: 10000 });
    await page.getByRole('button', { name: 'Proceed to Analysis' }).click();

    // Step 3: Analysis
    await expect(page.getByText('Analysis Dashboard')).toBeVisible();
    await expect(page.getByText('95.00%')).toBeVisible(); // Accuracy
    await expect(page.getByText('Confusion Matrix')).toBeVisible();
    await page.getByRole('button', { name: 'Proceed to Testing' }).click();

    // Step 4: Testing
    await expect(page.getByText('Batch Testing')).toBeVisible();
    await page.getByRole('button', { name: 'Run Inference' }).click();
    await expect(page.getByRole('cell', { name: 'Low' })).toBeVisible(); // Risk level from mock
    await page.getByRole('button', { name: 'Proceed to Deployment' }).click();

    // Step 5: Deployment
    await expect(page.getByRole('heading', { name: 'Deployment' })).toBeVisible();
    await expect(page.getByText('Ready to Deploy')).toBeVisible();
    
    // Handle alert dialog
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Deploy to Production' }).click();
    
    // Verify success
    await expect(page.getByText('System updated. New model is now handling live traffic.')).toBeVisible();
  });
});
