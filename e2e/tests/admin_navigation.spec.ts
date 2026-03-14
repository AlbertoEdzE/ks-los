import { test, expect } from '@playwright/test';

test.describe('Admin Panel Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();
  });

  test('Sidebar navigation works', async ({ page }) => {
    // Check initial state
    await expect(page.getByRole('heading', { name: 'Synthetic Data Generator' })).toBeVisible();

    // Click Configuration
    await page.getByRole('button', { name: 'Configuration' }).click();
    await expect(page.getByRole('heading', { name: 'System Configuration' })).toBeVisible();

    // Click Simulator
    await page.getByRole('button', { name: 'Simulator' }).click();
    await expect(page.getByRole('heading', { name: 'Model Simulator' })).toBeVisible();

    // Click Metrics
    await page.getByRole('button', { name: 'Metrics' }).click();
    await expect(page.getByRole('heading', { name: 'Metrics' })).toBeVisible();

    // Click Leads
    await page.route('http://localhost:8000/api/conversations', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.getByRole('button', { name: 'Leads' }).click();
    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

    // Click Loans (mocked backend)
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

    await page.route('http://localhost:8000/api/catalog-products', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'p1', name: 'Home Standard', code: 'HOME_STD', requiredDocuments: [docName], status: 'active' },
        ]),
      });
    });
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

    await page.getByRole('button', { name: 'Loans' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('text-doc-checklist-title')).toBeVisible();
    await page.getByTestId(`select-doc-status-${docName}`).selectOption('submitted');
    await expect(page.getByTestId(`doc-status-${docName}`)).toHaveText('submitted');

    // Click Training
    await page.getByRole('button', { name: 'ML Training' }).click();
    await expect(page.getByRole('heading', { name: 'ML Model Training Pipeline' })).toBeVisible();
  });

  test('Document checklist status persists via real backend', async ({ page }) => {
    const officerHeaders = { 'x-officer-role': 'loan-officer-access' };

    const health = await page.request.get('http://localhost:8000/health');
    expect(health.status()).toBe(200);

    const seed = await page.request.post('http://localhost:8000/admin/seed/v2-baseline?reset=true', { headers: officerHeaders });
    expect(seed.status()).toBe(200);

    const borrowerName = `E2E Checklist ${Date.now()}`;
    const createLoan = await page.request.post('http://localhost:8000/api/loans', {
      headers: { ...officerHeaders, 'Content-Type': 'application/json' },
      data: {
        borrowerName,
        loanType: 'Home Loan',
        loanAmount: '250000',
        catalogProductCode: 'HL-PUR-001',
      },
    });
    expect(createLoan.status()).toBe(200);
    const createdLoan = (await createLoan.json()) as { id: string };
    const loanId = createdLoan.id;

    await page.getByRole('button', { name: 'Loans' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();

    await expect(page.getByTestId(`loan-row-${loanId}`)).toBeVisible({ timeout: 30000 });
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('text-doc-checklist-title')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('select-doc-status-PAN Card').selectOption('submitted');
    await expect(page.getByTestId('doc-status-PAN Card')).toHaveText('submitted');

    const getLoan = await page.request.get(`http://localhost:8000/api/loans/${loanId}`, { headers: officerHeaders });
    expect(getLoan.status()).toBe(200);
    const loanPayload = (await getLoan.json()) as {
      documentChecklist?: { items: Array<{ name: string; status: string }> };
    };
    const panItem = loanPayload.documentChecklist?.items.find((i) => i.name === 'PAN Card');
    expect(panItem?.status).toBe('submitted');

    await page.reload();
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();

    await page.getByRole('button', { name: 'Loans' }).click();
    await expect(page.getByRole('heading', { name: 'Loans' })).toBeVisible();
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('doc-status-PAN Card')).toHaveText('submitted');
  });

  test('Training tab shows steps', async ({ page }) => {
    await page.getByRole('button', { name: 'ML Training' }).click();
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
