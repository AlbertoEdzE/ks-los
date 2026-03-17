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
    const phases = (await phasesResponse.json()) as Array<{ id?: string; name?: string }>;
    const firstPhaseId = phases[0]?.id;
    const firstPhaseName = phases[0]?.name;
    expect(firstPhaseId).toBeTruthy();
    expect(firstPhaseName).toBeTruthy();

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

    await page.getByTestId(`pipeline-phase-header-${firstPhaseId as string}`).click();
    await expect(page.getByTestId('phase-title')).toContainText(firstPhaseName as string);
    await expect(page.getByTestId('card-summary')).toBeVisible();
    await expect(page.getByTestId('text-phase-summary')).toBeVisible();
    await expect(page.getByTestId('phase-timeline')).toBeVisible();
    await expect(page.getByTestId('phase-loan-count')).toBeVisible();
    await expect(page.getByTestId('phase-conversation-count')).toBeVisible();
    await expect(page.getByTestId('card-activities')).toBeVisible();
    await expect(page.getByTestId('card-documents')).toBeVisible();
    await expect(page.getByTestId('card-stakeholders')).toBeVisible();
    await expect(page.getByTestId('card-bottlenecks')).toBeVisible();
    await expect(page.getByTestId('text-activity-0')).toBeVisible();

    await page.getByTestId('phase-back-link').click();
    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

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

    const assistantMsgs = page.getByTestId('officer-chat-message-assistant');

    await expect(page.getByTestId('officer-chat-leads')).toBeVisible();
    await page.getByTestId(`officer-chat-lead-${conversationId as string}`).click();
    await expect(assistantMsgs).toHaveCount(1, { timeout: 20000 });

    await page.getByTestId('officer-chat-input').fill('Assign officer to officer-99');
    const beforeAssign = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeAssign + 1, { timeout: 20000 });

    const leadRow = page.getByTestId(`officer-chat-lead-${conversationId as string}`);
    await expect(leadRow).toContainText('Officer: officer-99', { timeout: 20000 });

    await page.getByTestId('officer-chat-input').fill('Set status to reviewing');
    const beforeStatus = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeStatus + 1, { timeout: 20000 });
    await expect(leadRow).toContainText('reviewing', { timeout: 20000 });

    const chatBorrowerName = `E2E Chat Loan ${Date.now()}`;
    await page.getByTestId('officer-chat-input').fill(`Create loan for ${chatBorrowerName} $310000`);
    const beforeCreateLoan = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeCreateLoan + 1, { timeout: 20000 });

    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('create_loan', { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('success', { timeout: 20000 });

    const lastAssistantText = await assistantMsgs.last().innerText();
    const uuidMatch = lastAssistantText.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
    expect(uuidMatch).toBeTruthy();
    const chatLoanId = uuidMatch?.[0] as string;

    await page.getByTestId('officer-chat-input').fill(`Move loan ${chatLoanId} to phase ${firstPhaseName as string}`);
    const beforeMoveLoan = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeMoveLoan + 1, { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('move_loan_phase', { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('success', { timeout: 20000 });

    await page.getByRole('link', { name: 'Pipeline', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await expect(page.getByTestId(`pipeline-group-${firstPhaseId as string}`)).toContainText(chatBorrowerName, { timeout: 20000 });

    await page.getByRole('link', { name: 'Officer Chat' }).click();
    await expect(page.getByTestId('heading-officer-chat')).toBeVisible();

    const newPhaseName = `E2E QA Phase ${Date.now()}`;
    await page.getByTestId('officer-chat-input').fill(`Add phase ${newPhaseName}`);
    const beforeAddPhase = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeAddPhase + 1, { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('add_phase', { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('success', { timeout: 20000 });

    const phasesAfterAddResponse = await page.request.get('http://localhost:8000/api/phases');
    const phasesAfterAdd = (await phasesAfterAddResponse.json()) as Array<{ id?: string; name?: string; isActive?: boolean }>;
    const newPhase = phasesAfterAdd.find((p) => (p.name || '').toLowerCase() === newPhaseName.toLowerCase());
    expect(newPhase?.id).toBeTruthy();
    const newPhaseId = newPhase?.id as string;

    await page.getByRole('link', { name: 'Pipeline', exact: true }).click();
    await expect(page.getByTestId(`pipeline-group-${newPhaseId}`)).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId(`pipeline-group-${newPhaseId}`)).toContainText(newPhaseName);

    await page.getByRole('link', { name: 'Officer Chat' }).click();
    await page.getByTestId('officer-chat-input').fill(`Deactivate phase ${newPhaseName}`);
    const beforeDeactivate = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeDeactivate + 1, { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('set_phase_active', { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('success', { timeout: 20000 });

    await page.getByRole('link', { name: 'Pipeline', exact: true }).click();
    await expect(page.getByTestId(`pipeline-group-${newPhaseId}`)).toHaveCount(0);

    await page.getByRole('link', { name: 'Officer Chat' }).click();
    await page.getByTestId('officer-chat-input').fill(`Activate phase ${newPhaseName}`);
    const beforeActivate = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeActivate + 1, { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('set_phase_active', { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('success', { timeout: 20000 });

    const phasesBeforeReorderResponse = await page.request.get('http://localhost:8000/api/phases');
    const phasesBeforeReorder = (await phasesBeforeReorderResponse.json()) as Array<{ id?: string; name?: string; isActive?: boolean }>;
    const originalNames = phasesBeforeReorder.map((p) => p.name).filter(Boolean) as string[];
    expect(originalNames.length).toBeGreaterThan(1);
    const reversedNames = [...originalNames].reverse();

    await page.getByTestId('officer-chat-input').fill(`Reorder phases to: ${reversedNames.join(' > ')}`);
    const beforeReorder = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeReorder + 1, { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('reorder_phases', { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('success', { timeout: 20000 });

    const phasesAfterReorderResponse = await page.request.get('http://localhost:8000/api/phases');
    const phasesAfterReorder = (await phasesAfterReorderResponse.json()) as Array<{ id?: string; name?: string; isActive?: boolean }>;
    const firstAfterReorder = phasesAfterReorder.find((p) => p.isActive !== false);
    expect(firstAfterReorder?.id).toBeTruthy();
    const firstAfterReorderId = firstAfterReorder?.id as string;

    await page.getByRole('link', { name: 'Pipeline', exact: true }).click();
    const groupBlocks = page.locator('[data-testid^="pipeline-group-"]');
    await expect(groupBlocks.nth(0)).toHaveAttribute('data-testid', 'pipeline-group-unassigned');
    await expect(groupBlocks.nth(1)).toHaveAttribute('data-testid', `pipeline-group-${firstAfterReorderId}`);

    await page.getByRole('link', { name: 'Officer Chat' }).click();
    await page.getByTestId('officer-chat-input').fill(`Reorder phases to: ${originalNames.join(' > ')}`);
    const beforeReorderBack = await assistantMsgs.count();
    await page.getByTestId('officer-chat-send').click();
    await expect(assistantMsgs).toHaveCount(beforeReorderBack + 1, { timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('officer-chat-action-results')).toContainText('reorder_phases', { timeout: 20000 });

    await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
      headers: { 'x-officer-role': 'loan-officer-access' },
    });
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
