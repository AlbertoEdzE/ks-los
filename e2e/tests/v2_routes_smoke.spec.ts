import { test, expect } from '@playwright/test';

test.describe('V2 Route Skeleton', () => {
  test('Officer routes render and navigate', async ({ page }) => {
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

    const phasesResponse = await page.request.get('http://localhost:8000/api/phases');
    const phases = (await phasesResponse.json()) as Array<{ id?: string }>;
    const firstPhaseId = phases[0]?.id;
    expect(firstPhaseId).toBeTruthy();

    const borrowerName = `E2E Phase Group ${Date.now()}`;
    const createdLoan = await page.request.post('http://localhost:8000/api/loans', {
      headers: { 'content-type': 'application/json', 'x-officer-role': 'loan-officer-access' },
      data: {
        borrowerName,
        loanType: 'home_loan',
        loanAmount: '250000',
        catalogProductCode: 'HL-PUR-001',
        conversationId,
        createdBy: 'e2e',
      },
    });
    const createdLoanPayload = (await createdLoan.json()) as { id?: string };
    const loanId = createdLoanPayload.id;
    expect(loanId).toBeTruthy();

    await page.request.patch(`http://localhost:8000/api/loans/${loanId as string}`, {
      headers: { 'content-type': 'application/json', 'x-officer-role': 'loan-officer-access' },
      data: { currentPhaseId: firstPhaseId },
    });

    await page.goto('/dashboard');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Pipeline' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Loan Products' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Officer Chat' })).toBeVisible();

    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

    await page.getByRole('link', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await expect(page.getByTestId(`pipeline-group-${firstPhaseId as string}`)).toContainText(borrowerName, { timeout: 20000 });
    await expect(page.getByTestId(`loan-row-${loanId as string}`)).toBeVisible({ timeout: 20000 });

    await page.getByRole('link', { name: 'Loan Products' }).click();
    await expect(page.getByTestId('heading-loan-products')).toBeVisible();
    await expect(page.getByTestId('loan-product-HL-PUR-001')).toBeVisible();

    await page.getByTestId('button-create-product').click();
    await expect(page.getByTestId('product-form')).toBeVisible();
    await page.getByTestId('input-create-name').fill('Test Product');
    await page.getByTestId('input-create-code').fill('E2E-TP-001');
    await page.getByTestId('select-create-category').selectOption('personal_loan');
    await page.getByTestId('select-create-status').selectOption('active');
    await page.getByTestId('button-save-create').click();
    const createdCard = page.getByTestId('loan-product-E2E-TP-001');
    await expect(createdCard).toBeVisible();

    await createdCard.getByRole('button', { name: 'Edit' }).click();
    await page.getByTestId('select-edit-status').selectOption('inactive');
    await page.getByTestId('button-save-edit').click();
    await expect(page.getByTestId('loan-product-E2E-TP-001')).toContainText('inactive');

    await page.getByRole('link', { name: 'Officer Chat' }).click();
    await expect(page.getByTestId('heading-officer-chat')).toBeVisible();

    await expect(page.getByTestId('officer-chat-leads')).toBeVisible();
    await page.getByTestId(`officer-chat-lead-${conversationId as string}`).click();
    await expect(page.getByTestId('officer-chat-message-assistant')).toHaveCount(1, { timeout: 20000 });

    await page.getByTestId('officer-chat-input').fill('Assign officer to officer-99');
    await page.getByTestId('officer-chat-send').click();
    await expect(page.getByTestId('officer-chat-message-assistant')).toHaveCount(2, { timeout: 20000 });

    const leadRow = page.getByTestId(`officer-chat-lead-${conversationId as string}`);
    await expect(leadRow).toContainText('Officer: officer-99', { timeout: 20000 });

    await page.getByTestId('officer-chat-input').fill('Set status to reviewing');
    await page.getByTestId('officer-chat-send').click();
    await expect(page.getByTestId('officer-chat-message-assistant')).toHaveCount(3, { timeout: 20000 });
    await expect(leadRow).toContainText('reviewing', { timeout: 20000 });
  });

  test('Borrower route renders after login', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Username').fill('demo');
    await page.getByLabel('Password').fill('demo123');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByTestId('text-app-title')).toHaveText('LoanAssist AI');
    await expect(page.getByRole('button', { name: 'Logout' })).toBeVisible();
  });

  test('Login inputs keep focus while typing', async ({ page }) => {
    await page.goto('/login');
    const username = page.getByLabel('Username');
    const password = page.getByLabel('Password');

    await username.click();
    await username.type('demo', { delay: 10 });
    await expect(username).toHaveValue('demo');

    await password.click();
    await password.type('demo123', { delay: 10 });
    await expect(password).toHaveValue('demo123');
  });
});
