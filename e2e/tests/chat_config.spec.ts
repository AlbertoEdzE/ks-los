import { test, expect } from '@playwright/test';

test('borrower chat shows suggestions and phase tracker', async ({ page }) => {
  await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
    headers: { 'x-officer-role': 'loan-officer-access' },
  });
  await page.addInitScript(() => {
    window.localStorage.removeItem('v2_borrower_conversation_id');
  });

  await page.goto('/login');
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByTestId('text-app-title')).toHaveText('LoanAssist AI');
  await expect(page.getByRole('heading', { name: 'Tell me what you need' })).toBeVisible();

  const homeLoanButton = page.getByRole('button', { name: /Home Loan/i });
  await expect(homeLoanButton).toBeVisible({ timeout: 10000 });

  await homeLoanButton.click();
  await expect(page.getByTestId('chat-message-user')).toHaveCount(1, { timeout: 20000 });
  await expect(page.getByTestId('chat-message-assistant')).toHaveCount(1, { timeout: 20000 });
  await expect(page.getByTestId('chat-message-assistant').first()).toContainText('What loan amount', { timeout: 20000 });

  await expect(page.getByTestId('phase-progress-tracker')).toBeVisible({ timeout: 20000 });
  await expect(page.getByTestId('recommended-products')).toBeVisible({ timeout: 20000 });
  await expect(page.getByText('Home Purchase Loan')).toBeVisible({ timeout: 20000 });
  await expect(page.getByTestId('next-conversation-angle')).not.toHaveText('—', { timeout: 20000 });
});

test('debt consolidation recommends personal loan products', async ({ page }) => {
  await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
    headers: { 'x-officer-role': 'loan-officer-access' },
  });
  await page.addInitScript(() => {
    window.localStorage.removeItem('v2_borrower_conversation_id');
  });

  await page.goto('/login');
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page.getByRole('heading', { name: 'Tell me what you need' })).toBeVisible();
  const debtButton = page.getByRole('button', { name: /Debt Consolidation/i });
  await debtButton.click();

  await expect(page.getByTestId('recommended-products')).toBeVisible({ timeout: 20000 });
  await expect(page.getByText('Personal Loan — Salaried')).toBeVisible({ timeout: 20000 });
});

test('phase tracker navigates to phase detail view', async ({ page }) => {
  await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
    headers: { 'x-officer-role': 'loan-officer-access' },
  });
  await page.addInitScript(() => {
    window.localStorage.removeItem('v2_borrower_conversation_id');
  });

  await page.goto('/login');
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page.getByRole('heading', { name: 'Tell me what you need' })).toBeVisible();
  await page.getByRole('button', { name: /Home Loan/i }).click();

  await expect(page.getByTestId('phase-progress-tracker')).toBeVisible({ timeout: 20000 });
  await page.getByTestId('phase-step-0').click();

  await expect(page).toHaveURL(/\/phases\/.+/);
  await expect(page.getByTestId('phase-title')).toBeVisible({ timeout: 20000 });
  await expect(page.getByTestId('phase-list')).toBeVisible({ timeout: 20000 });
  await expect(page.getByTestId('phase-list-item-selected')).toBeVisible({ timeout: 20000 });
});

test('borrower chat hides officer-only notes from the thread', async ({ page }) => {
  await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
    headers: { 'x-officer-role': 'loan-officer-access' },
  });

  const createdConversation = await page.request.post('http://localhost:8000/api/conversations', {
    headers: { 'content-type': 'application/json' },
    data: { chatRole: 'borrower' },
  });
  const createdPayload = (await createdConversation.json()) as { conversation?: { id?: string } };
  const conversationId = createdPayload.conversation?.id;
  expect(conversationId).toBeTruthy();

  await page.request.post(`http://localhost:8000/api/conversations/${conversationId as string}/messages`, {
    headers: { 'content-type': 'application/json', 'x-officer-role': 'loan-officer-access' },
    data: { content: 'OFFICER_INTERNAL_NOTE_DO_NOT_SHOW' },
  });

  await page.addInitScript((id) => {
    window.localStorage.setItem('v2_borrower_conversation_id', id);
  }, conversationId as string);

  await page.goto('/login');
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page.getByRole('heading', { name: 'Tell me what you need' })).toBeVisible();
  await expect(page.getByText('OFFICER_INTERNAL_NOTE_DO_NOT_SHOW')).toHaveCount(0);
});
