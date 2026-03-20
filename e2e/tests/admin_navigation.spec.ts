import { test, expect } from '@playwright/test';

test.describe('Admin Panel Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByLabel('Username').fill('officer');
    await page.getByLabel('Password').fill('Password123!');
    await page.getByRole('button', { name: 'Sign In' }).click();
  });

  test('Sidebar navigation works', async ({ page }) => {
    // Check initial state
    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

    await page.getByRole('link', { name: 'Configuration' }).click();
    await expect(page.getByRole('heading', { name: 'System Configuration' })).toBeVisible();

    await page.getByRole('link', { name: 'Simulator' }).click();
    await expect(page.getByRole('heading', { name: 'Model Simulator' })).toBeVisible();

    await page.getByRole('link', { name: 'Metrics' }).click();
    await expect(page.getByRole('heading', { name: 'Metrics' })).toBeVisible();

    await page.getByRole('link', { name: 'Dashboard' }).click();
    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

    // Pipeline (mocked backend)
    const loanId = 'loan-1';
    const docName = 'Government ID';
    let loan = {
      id: loanId,
      borrowerName: 'Alice Example',
      borrowerEmail: null,
      borrowerPhone: null,
      loanType: 'Home Loan',
      loanAmount: '250000',
      interestRate: null,
      tenure: null,
      monthlyEmi: null,
      purpose: null,
      employmentType: null,
      monthlyIncome: null,
      existingDebts: null,
      creditScore: null,
      collateral: null,
      downPayment: null,
      propertyValue: null,
      ltv: null,
      currentPhaseId: null,
      catalogProductCode: 'HOME_STD',
      documentChecklist: {
        productCode: 'HOME_STD',
        items: [{ name: docName, status: 'missing', updatedAt: '2026-01-01T00:00:00.000Z' }],
        asOf: '2026-01-01T00:00:00.000Z',
      },
      status: 'draft',
      notes: null,
      conversationId: null,
      createdBy: null,
      createdAt: '2026-01-01T00:00:00.000Z',
      updatedAt: '2026-01-01T00:00:00.000Z',
    };

    await page.route('http://localhost:8000/api/loans', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([loan]) });
        return;
      }
      await route.fulfill({ status: 405, body: '' });
    });
    await page.route(`http://localhost:8000/api/loans/${loanId}/documents`, async (route) => {
      const payload = route.request().postDataJSON() as { name: string; status: string };
      loan = {
        ...loan,
        documentChecklist: {
          ...loan.documentChecklist,
          items: loan.documentChecklist.items.map((i: any) =>
            i.name === payload.name ? { ...i, status: payload.status, updatedAt: '2026-01-01T00:00:10.000Z' } : i
          ),
          asOf: '2026-01-01T00:00:10.000Z',
        },
      };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(loan) });
    });

    await page.getByRole('link', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('text-doc-checklist-title')).toBeVisible();
    await page.getByTestId(`select-doc-status-${docName}`).selectOption('submitted');
    await expect(page.getByTestId(`doc-status-${docName}`)).toHaveText('submitted');

    await page.getByRole('link', { name: 'ML Training' }).click();
    await expect(page.getByRole('heading', { name: 'ML Model Training Pipeline' })).toBeVisible();
  });

  test('Document checklist status persists via real backend', async ({ page }) => {
    const loanId = `loan-${Date.now()}`;
    const borrowerName = `E2E Checklist ${Date.now()}`;
    let loan = {
      id: loanId,
      borrowerName,
      borrowerEmail: null,
      borrowerPhone: null,
      loanType: 'Home Loan',
      loanAmount: '250000',
      interestRate: null,
      tenure: null,
      monthlyEmi: null,
      purpose: null,
      employmentType: null,
      monthlyIncome: null,
      existingDebts: null,
      creditScore: null,
      collateral: null,
      downPayment: null,
      propertyValue: null,
      ltv: null,
      currentPhaseId: null,
      catalogProductCode: 'HL-PUR-001',
      documentChecklist: {
        productCode: 'HL-PUR-001',
        items: [{ name: 'PAN Card', status: 'missing', updatedAt: '2026-01-01T00:00:00.000Z' }],
        asOf: '2026-01-01T00:00:00.000Z',
      },
      status: 'draft',
      notes: null,
      conversationId: null,
      createdBy: null,
      createdAt: '2026-01-01T00:00:00.000Z',
      updatedAt: '2026-01-01T00:00:00.000Z',
    };

    await page.route('http://localhost:8000/api/loans', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([loan]) });
        return;
      }
      await route.fulfill({ status: 405, body: '' });
    });

    await page.route(`http://localhost:8000/api/loans/${loanId}/documents`, async (route) => {
      const payload = route.request().postDataJSON() as { name: string; status: string };
      loan = {
        ...loan,
        documentChecklist: {
          ...loan.documentChecklist,
          items: loan.documentChecklist.items.map((i: any) =>
            i.name === payload.name ? { ...i, status: payload.status, updatedAt: '2026-01-01T00:00:10.000Z' } : i
          ),
          asOf: '2026-01-01T00:00:10.000Z',
        },
      };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(loan) });
    });

    await page.getByRole('link', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();

    await expect(page.getByTestId(`loan-row-${loanId}`)).toBeVisible({ timeout: 30000 });
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('text-doc-checklist-title')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('select-doc-status-PAN Card').selectOption('submitted');
    await expect(page.getByTestId('doc-status-PAN Card')).toHaveText('submitted');

    await page.reload();
    try {
      await page.getByLabel('Username').waitFor({ state: 'visible', timeout: 3000 });
      await page.getByLabel('Username').fill('officer');
      await page.getByLabel('Password').fill('Password123!');
      await page.getByRole('button', { name: 'Sign In' }).click();
    } catch {
      // already logged in
    }

    await page.getByRole('link', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('doc-status-PAN Card')).toHaveText('submitted');
  });

  test('Document upload, extraction, and signature work via real backend', async ({ page }) => {
    await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', {
      headers: { authorization: 'Bearer loan-officer-access' },
    });

    const productCode = `E2E-DOC-${Date.now()}`;
    await page.request.post('http://localhost:8000/api/catalog-products', {
      headers: { 'content-type': 'application/json', authorization: 'Bearer loan-officer-access' },
      data: {
        name: `E2E Docs ${Date.now()}`,
        code: productCode,
        category: 'kyc',
        requiredDocuments: ['Passport', 'Job Letter'],
        status: 'active',
      },
    });

    const borrowerName = `E2E Upload ${Date.now()}`;
    const createdLoan = await page.request.post('http://localhost:8000/api/loans', {
      headers: { 'content-type': 'application/json', authorization: 'Bearer loan-officer-access' },
      data: {
        borrowerName,
        loanType: 'home_loan',
        loanAmount: '250000',
        catalogProductCode: productCode,
        createdBy: 'e2e',
      },
    });
    const createdLoanPayload = (await createdLoan.json()) as { id?: string };
    const loanId = createdLoanPayload.id;
    expect(loanId).toBeTruthy();

    await page.getByRole('link', { name: 'Pipeline' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await expect(page.getByTestId(`loan-row-${loanId as string}`)).toBeVisible({ timeout: 30000 });
    await page.getByTestId(`loan-row-${loanId as string}`).click();
    await expect(page.getByTestId('text-doc-checklist-title')).toBeVisible({ timeout: 30000 });

    await page.getByTestId('input-doc-upload-0').setInputFiles('/Users/albertohernandez/Downloads/passport-example.png');
    await expect(page.getByTestId('doc-status-Passport')).toHaveText('submitted', { timeout: 60000 });
    await expect(page.getByTestId('doc-uploaded-file-0')).toContainText('passport-example.png', { timeout: 60000 });

    await page.getByTestId('input-doc-upload-1').setInputFiles('/Users/albertohernandez/Downloads/job-letter.pdf');
    await expect(page.getByTestId('doc-status-Job Letter')).toHaveText('submitted', { timeout: 60000 });
    await expect(page.getByTestId('doc-uploaded-file-1')).toContainText('job-letter.pdf', { timeout: 60000 });
    await expect(page.getByTestId('doc-extracted-preview-1')).toHaveText(/.{10,}/, { timeout: 60000 });

    const canvas = page.getByTestId('canvas-signature');
    const box = await canvas.boundingBox();
    expect(box).toBeTruthy();
    const startX = (box as any).x + 40;
    const startY = (box as any).y + 60;
    await page.mouse.move(startX, startY);
    await page.mouse.down();
    await page.mouse.move(startX + 240, startY + 10, { steps: 12 });
    await page.mouse.up();

    await page.getByTestId('button-signature-save').click();
    await expect(page.getByTestId('select-doc-status-Signature')).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId('doc-status-Signature')).toHaveText('submitted', { timeout: 30000 });
  });

  test('Training tab shows steps', async ({ page }) => {
    await page.getByRole('link', { name: 'ML Training' }).click();
    await page.getByRole('button', { name: 'Training Workflow' }).click();
    
    // Check steps
    await expect(page.getByText('Execution')).toBeVisible();
    await expect(page.getByText('Testing')).toBeVisible();
    await expect(page.getByText('Deployment')).toBeVisible();

    // Check Planning content
    await expect(page.getByRole('heading', { name: 'Configuration & Planning' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate Training Plan' })).toBeVisible();
  });
});
