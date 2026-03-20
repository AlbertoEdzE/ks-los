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
    await page.getByTestId('select-borrower').click();
    await page.getByLabel('Username').fill('borrower');
    await page.getByLabel('Password').fill('Password123!');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByTestId('text-app-title')).toHaveText('LoanAssist AI');
    await expect(page.getByTestId('borrower-greeting')).toBeVisible();
    await page.getByRole('button', { name: /Home Loan/i }).click();

    await expect(page.getByTestId('chat-message-user')).toHaveCount(1, { timeout: 20000 });
    await expect(page.getByTestId('chat-message-assistant')).toHaveCount(1, { timeout: 20000 });
    await expect(page.getByTestId('phase-progress-tracker')).toBeVisible({ timeout: 20000 });
    const recommendationsCard = page.getByTestId('card-recommendations');
    await recommendationsCard.scrollIntoViewIfNeeded();
    await expect(recommendationsCard).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('recommended-product-0')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('approval-probability')).toBeVisible({ timeout: 20000 });

    await page.getByTestId('input-chat-message').fill('loan amount: 350000 USD, income: 10000 USD/month, salaried');
    await page.getByTestId('button-send-message').click();
    await expect(page.getByTestId('chat-message-user')).toHaveCount(2, { timeout: 20000 });
    await expect(page.getByTestId('chat-message-assistant')).toHaveCount(2, { timeout: 20000 });
    await expect(page.getByTestId('approval-probability')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('approval-blocker-0')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('approval-action-0')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('borrower-doc-upload-panel')).toHaveCount(0);

    await page.getByTestId('input-chat-message').fill('Tenure: 10 years. No debts.');
    await page.getByTestId('button-send-message').click();
    await expect(page.getByTestId('chat-message-user')).toHaveCount(3, { timeout: 20000 });
    await expect(page.getByTestId('chat-message-assistant')).toHaveCount(3, { timeout: 20000 });

    await page.getByTestId('button-attachments').click();
    const docPanel = page.getByTestId('borrower-doc-upload-panel');
    await docPanel.scrollIntoViewIfNeeded();
    await expect(docPanel).toBeVisible({ timeout: 20000 });

    await page.getByTestId('button-doc-category-identity').click();

    const uploadWithBuffer = async (buttonTestId: string, fileName: string, mimeType: string, buf: Buffer) => {
      const chooserPromise = page.waitForEvent('filechooser');
      await page.getByTestId(buttonTestId).click();
      const chooser = await chooserPromise;
      await chooser.setFiles({ name: fileName, mimeType, buffer: buf });
      await expect(page.getByText(fileName)).toBeVisible({ timeout: 20000 });
    };

    const tinyPng = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/aa2x0QAAAAASUVORK5CYII=',
      'base64',
    );

    await uploadWithBuffer('button-doc-upload-identity-national_id', 'id.png', 'image/png', tinyPng);
    await page.getByTestId('button-doc-category-income_salaried').click();
    await uploadWithBuffer('button-doc-upload-income_salaried-job_letter', 'job-letter.pdf', 'application/pdf', tinyPng);

    const offerCard = page.getByTestId('stp-offer-card');
    try {
      await expect(offerCard).toBeVisible({ timeout: 10000 });
    } catch {
      const runChecks = page.getByTestId('button-run-stp');
      await runChecks.scrollIntoViewIfNeeded();
      await runChecks.click();
      await expect(offerCard).toBeVisible({ timeout: 20000 });
    }

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

    const convId = await page.evaluate(() => window.localStorage.getItem('v2_borrower_conversation_id'));
    expect(convId).toBeTruthy();
    const msgRes = await page.request.get(`http://localhost:8000/api/conversations/${convId}/messages`);
    expect(msgRes.status()).toBe(200);
    const msgs = (await msgRes.json()) as Array<{ role?: string; metadata?: unknown }>;
    const lastAssistant = [...msgs].reverse().find((m) => m && m.role === 'assistant');
    expect(lastAssistant).toBeTruthy();
    const meta = (lastAssistant as { metadata?: any }).metadata;
    expect(meta && typeof meta === 'object' && meta.finalRecommendation && typeof meta.finalRecommendation === 'object').toBeTruthy();
  });
});
