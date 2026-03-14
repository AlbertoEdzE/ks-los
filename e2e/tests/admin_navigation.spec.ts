import { test, expect } from '@playwright/test';

test.describe('Admin Panel Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: 'Login' }).click();
  });

  test('Sidebar navigation works', async ({ page }) => {
    // Check initial state
    await expect(page.getByRole('heading', { name: 'Leads' })).toBeVisible();

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

    await page.route('http://localhost:8000/api/catalog-products', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'p1', name: 'Home Purchase', code: 'HL-PUR-001', requiredDocuments: ['PAN Card'], status: 'active' },
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

    await page.route(`http://localhost:8000/api/loans/${loanId}`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(loan) });
        return;
      }
      await route.fallback();
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

    await expect(page.getByTestId(`loan-row-${loanId}`)).toBeVisible({ timeout: 30000 });
    await page.getByTestId(`loan-row-${loanId}`).click();
    await expect(page.getByTestId('text-doc-checklist-title')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('select-doc-status-PAN Card').selectOption('submitted');
    await expect(page.getByTestId('doc-status-PAN Card')).toHaveText('submitted');

    await page.reload();
    try {
      await page.getByLabel('Username').waitFor({ state: 'visible', timeout: 3000 });
      await page.getByLabel('Username').fill('admin');
      await page.getByLabel('Password').fill('admin123');
      await page.getByRole('button', { name: 'Login' }).click();
    } catch {
      // already logged in
    }

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
