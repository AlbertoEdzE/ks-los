import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('Complete chat flow with suggestions and progress bar', async ({ page }) => {
    // Increase test timeout to handle slow LLM responses
    test.setTimeout(120000);

    await page.route('http://localhost:8000/chat/suggestions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: ['Katie Brady, Antigua and Barbuda, 34 years old'] }),
      });
    });

    await page.route('http://localhost:8000/agent/chat', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'Profile generated.',
          credit_profile: {
            metadata: {
              source: 'synthetic',
              query_timestamp: '2026-01-01T00:00:00',
              territory: 'AG',
              consent_token: 'token',
              synthetic_archetype: 'TEST_ARCHETYPE',
            },
            identity: {
              full_name: 'Katie Brady',
              date_of_birth: '1992-01-01',
              national_id_hash: 'hash',
              address: {
                line1: '123 Main St',
                city: "St John's",
                territory: 'Antigua and Barbuda',
                territory_code: 'AG',
              },
            },
            summary: {
              credit_score: 750,
              score_band: 'GOOD',
              total_accounts: 5,
              open_accounts: 5,
              closed_accounts: 0,
              total_credit_limit_xcd: 50000,
              total_current_balance_xcd: 10000,
              utilization_ratio: 0.2,
              total_past_due_xcd: 0,
              months_oldest_account: 60,
              months_newest_account: 12,
              derogatory_marks: 0,
              thin_file: false,
            },
            payment_behavior: {
              on_time_payments_pct: 1.0,
              late_30_days_count: 0,
              late_60_days_count: 0,
              late_90_plus_days_count: 0,
              charge_offs: 0,
              collections: 0,
              worst_payment_status_ever: 'OK',
              payment_history_24m: '111111111111111111111111',
            },
            trade_lines: [
              {
                account_id_hash: 'acc1',
                creditor_type: 'BANK',
                account_type: 'CREDIT_CARD',
                opened_date: '2020-01-01',
                credit_limit_xcd: 10000,
                current_balance_xcd: 2000,
                monthly_payment_xcd: 500,
                account_status: 'CURRENT',
                payment_history_24m: '111111111111111111111111',
                ecoa_code: 'INDIVIDUAL',
              },
            ],
            inquiries: [],
            flags: {
              has_bankruptcy: false,
              has_foreclosure: false,
              has_active_collections: false,
              is_deceased: false,
              fraud_alert: false,
            },
          },
        }),
      });
    });

    // a. Log in
    await page.goto('/login');
    await page.getByPlaceholder('Enter username').fill('demo');
    await page.getByPlaceholder('Enter password').fill('demo123');
    await page.getByRole('button', { name: 'Login' }).click();

    // Verify chat interface loaded
    await expect(page.locator('h2', { hasText: 'Chat with Journey Coach' })).toBeVisible();

    // b. Verify suggestion strip appears
    await expect(page.getByText(/Quick Start|Suggested inputs/)).toBeVisible();
    
    const suggestionBtn = page.getByRole('button', { name: /katie brady/i }).first();
    await expect(suggestionBtn).toBeVisible();
    await suggestionBtn.click();

    await expect(page.getByText('Credit Summary')).toBeVisible({ timeout: 60000 });

    // c. Check that the progress bar appears (role="status")
    // It appears when profile is generated. This might happen after the 2nd or 3rd message depending on the flow.
    const progressBar = page.getByRole('status');
    await expect(progressBar).toBeVisible({ timeout: 60000 });
    
    // Check for step labels (any of the steps) inside the progress bar
    await expect(progressBar.getByText('Intake')).toBeVisible();
    
    await expect(page.getByText('Credit Summary')).toBeVisible({ timeout: 60000 });
  });
});
