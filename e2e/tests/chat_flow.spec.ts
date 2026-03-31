import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('Complete borrower v3 chat flow with phase tracker, real-time metrics, and STP completion', async ({ page }: any) => {
    test.setTimeout(240000);
    const env = (globalThis as any).process?.env ?? {};
    const apiBase = env.API_BASE_URL || 'http://localhost:8000';
    const v3Requests: string[] = [];
    const docUploadRequests: string[] = [];
    page.on('request', (req: any) => {
      const url = req.url();
      if (url.includes('/api/v3/conversations')) v3Requests.push(url);
      if (url.includes('/api/documents/upload')) docUploadRequests.push(url);
    });

    await page.request.post(`${apiBase}/admin/seed/v2-baseline?reset=true`, {
      headers: { authorization: 'Bearer loan-officer-access' },
    });
    await page.addInitScript(() => {
      window.localStorage.removeItem('v2_borrower_conversation_id');
    });

    // a. Log in
    await page.goto('/login');
    await page.getByTestId('select-borrower').click();
    await page.getByLabel('Username').fill('borrower');
    await page.getByLabel('Password').fill('Password123!');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByTestId('text-app-title')).toHaveText('LoanAssist AI');
    await expect(page.getByTestId('borrower-greeting')).toBeVisible();
    await page.getByRole('button', { name: /Home Loan/i }).click();

    await expect(page.getByTestId('chat-message-user')).toHaveCount(1, { timeout: 20000 });
    await expect(page.getByTestId('chat-message-assistant')).toHaveCount(1, { timeout: 20000 });
    await expect(page.getByTestId('borrower-journey-tracker')).toBeVisible({ timeout: 20000 });
    const recommendationsCard = page.getByTestId('card-recommendations');
    await recommendationsCard.scrollIntoViewIfNeeded();
    await expect(recommendationsCard).toBeVisible({ timeout: 20000 });
    try {
      await expect(page.getByTestId('recommended-product-0')).toBeVisible({ timeout: 10000 });
    } catch {
      await expect(recommendationsCard).toContainText('No recommendations yet', { timeout: 20000 });
    }

    await page.getByTestId('input-chat-message').fill('Loan amount: 350000 USD. Monthly income: 10000 USD. Employment: salaried. Tenure: 10 years. Existing debts: 0.');
    await page.getByTestId('button-send-message').click();
    await expect(page.getByTestId('approval-probability')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('stp-tier')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('risk-grade')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('foir')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('stp-tier')).not.toHaveText('—', { timeout: 20000 });
    await expect(page.getByTestId('risk-grade')).toHaveText(/^[A-Z]$/, { timeout: 20000 });
    await expect(page.getByTestId('foir')).toHaveText(/\d/, { timeout: 20000 });
    await expect(page.getByTestId('button-attachments')).toBeEnabled({ timeout: 20000 });

    const convId = await page.evaluate(() => window.localStorage.getItem('v2_borrower_conversation_id'));
    expect(convId).toBeTruthy();

    let loanId: string | null = null;
    for (let i = 0; i < 30; i++) {
      const loanRes = await page.request.get(`${apiBase}/api/v3/conversations/${convId}/loan`);
      if (loanRes.ok()) {
        const loan = (await loanRes.json().catch(() => null)) as any;
        if (loan && typeof loan.id === 'string' && loan.id) {
          loanId = loan.id;
          break;
        }
      }
      await page.waitForTimeout(500);
    }
    expect(loanId).toBeTruthy();

    const uploadNextDoc = async (fileName: string) => {
      const BufferAny = (globalThis as any).Buffer;
      const tinyPng = BufferAny.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/aa2x0QAAAAASUVORK5CYII=',
        'base64',
      );
      await page.getByTestId('button-attachments').click({ force: true });
      const fileInput = page.locator('input[type="file"].hidden[accept*=".pdf"]').first();
      await fileInput.setInputFiles({ name: fileName, mimeType: 'image/png', buffer: tinyPng });

      await expect(page.getByRole('heading', { name: fileName })).toBeVisible({ timeout: 20000 });

      const closeBtn = page.getByRole('button', { name: 'Close' });
      const previewIsOpen = await closeBtn.isVisible().catch(() => false);
      if (previewIsOpen) {
        await closeBtn.click({ force: true });
        await page.locator('div[data-state="open"].fixed.inset-0').first().waitFor({ state: 'hidden', timeout: 5000 }).catch(() => null);
      }
    };

    const suffix = String(Date.now());
    await uploadNextDoc(`national-id-${suffix}.png`);
    await uploadNextDoc(`income-proof-${suffix}.png`);

    const stpRes = await page.request.post(`${apiBase}/api/loans/${loanId}/stp-process`, {
      headers: { 'X-Conversation-ID': convId as string },
    });
    expect(stpRes.ok()).toBeTruthy();
    await page.getByTestId('input-chat-message').fill('Ok, please proceed.');
    await page.getByTestId('button-send-message').click({ force: true });

    const offerCard = page.getByTestId('stp-offer-card');
    await expect(offerCard).toBeVisible({ timeout: 60000 });

    await offerCard.scrollIntoViewIfNeeded();
    await page.getByTestId('checkbox-terms-accept').check();

    const canvas = page.getByTestId('canvas-terms-signature');
    const box = await canvas.boundingBox();
    expect(box).toBeTruthy();
    if (box) {
      await page.mouse.move(box.x + 20, box.y + 30);
      await page.mouse.down();
      await page.mouse.move(box.x + 220, box.y + 90);
      await page.mouse.up();
    }

    await page.getByTestId('button-terms-accept').click();
    await expect(page.getByTestId('disbursement-confirmation-card')).toBeVisible({ timeout: 20000 });

    expect(v3Requests.length).toBeGreaterThan(0);
    expect(docUploadRequests.length).toBeGreaterThan(0);
  });
});
