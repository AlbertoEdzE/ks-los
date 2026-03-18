import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('Complete borrower v2 chat flow with phase tracker and recommendations', async ({ page }) => {
    test.setTimeout(120000);
    await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
      headers: { authorization: 'Bearer loan-officer-access' },
    });
    await page.addInitScript(() => {
      window.localStorage.removeItem('v2_borrower_conversation_id');
    });

    // a. Log in
    await page.goto('/login');
    await page.getByPlaceholder('Enter username').fill('demo');
    await page.getByPlaceholder('Enter password').fill('demo123');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByTestId('text-app-title')).toHaveText('LoanAssist AI');
    await expect(page.getByRole('heading', { name: 'Tell me what you need' })).toBeVisible();
    await page.getByRole('button', { name: /Home Loan/i }).click();

    await expect(page.getByTestId('chat-message-user')).toHaveCount(1, { timeout: 20000 });
    await expect(page.getByTestId('chat-message-assistant')).toHaveCount(1, { timeout: 20000 });
    await expect(page.getByTestId('phase-progress-tracker')).toBeVisible({ timeout: 20000 });
    const recommendationsCard = page.getByTestId('card-recommendations');
    await recommendationsCard.scrollIntoViewIfNeeded();
    await expect(recommendationsCard).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('Home Purchase Loan')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('approval-probability')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('approval-blocker-0')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('approval-action-0')).toBeVisible({ timeout: 20000 });

    await page.getByTestId('input-chat-message').fill('fasdf');
    await page.getByTestId('button-send-message').click();
    await expect(page.getByTestId('chat-message-user')).toHaveCount(2, { timeout: 20000 });
    await expect(page.getByTestId('chat-message-assistant')).toHaveCount(2, { timeout: 20000 });
  });
});
