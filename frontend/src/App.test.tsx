import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function renderApp(initialEntries: string[]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders login screen initially', () => {
    try {
      renderApp(['/login']);
      expect(screen.getByText('Welcome to LoanAssist')).toBeInTheDocument();
    } catch (error) {
      console.error('App render failed:', error);
      throw error;
    }
  });

  it('allows officer to update lead details and persists on refresh', async () => {
    const leadId = 'lead-12345678';
    const baseLead = {
      id: leadId,
      borrowerName: null,
      status: 'active',
      chatRole: 'borrower',
      currentPhaseId: null,
      seriousnessScore: 10,
      fitScore: 55,
      intentSummary: null,
      approvalProbability: {
        probability: 0.6,
        band: 'medium',
        topBlockers: [{ title: 'Missing credit score', severity: 'high', detail: 'Credit score not provided yet.' }],
        topActions: [{ title: 'Share credit score range', impact: 'high', detail: 'Provide an estimated credit score or bureau range.' }],
        inputsUsed: { creditScore: null, monthlyIncome: null, existingDebts: null, loanAmount: null, dti: null, loanToIncome: null },
        method: 'heuristic_v1',
        asOf: '2026-03-17T00:00:00Z',
      },
      recommendedProducts: null,
      nextConversationAngle: null,
      assignedOfficer: null,
      createdAt: null,
    };

    const updatedLead = {
      ...baseLead,
      borrowerName: 'Jane Doe',
      assignedOfficer: 'officer-1',
      status: 'reviewing',
    };

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      const method = (init?.method || 'GET').toUpperCase();

      if (url.endsWith('/api/conversations') && method === 'GET') {
        return new Response(JSON.stringify([baseLead]), { status: 200 });
      }
      // Dashboard view also loads loans/phases in the background for cross-linking.
      if (url.endsWith('/api/loans') && method === 'GET') {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith('/api/phases') && method === 'GET') {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith(`/api/conversations/${leadId}`) && method === 'PATCH') {
        return new Response(JSON.stringify(updatedLead), { status: 200 });
      }
      return new Response('not found', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    renderApp(['/dashboard']);

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'officer' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await screen.findByRole('heading', { name: 'Dashboard' });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/conversations'), expect.anything());
    });

    fireEvent.click(await screen.findByTestId(`officer-hold-row-${leadId}`));
    expect(await screen.findByText('Approval Probability')).toBeInTheDocument();
    expect(screen.getByText('Top blockers')).toBeInTheDocument();
    expect(screen.getByText('Missing credit score')).toBeInTheDocument();
    expect(screen.getByText('Share credit score range')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('lead-borrower-name-input'), { target: { value: 'Jane Doe' } });
    fireEvent.change(screen.getByTestId('lead-assigned-officer-input'), { target: { value: 'officer-1' } });
    fireEvent.change(screen.getByTestId('lead-status-select'), { target: { value: 'reviewing' } });
    fireEvent.click(screen.getByTestId('lead-save-button'));

    await screen.findByText('Saved');
    expect(screen.getAllByText('Jane Doe').length).toBeGreaterThan(0);
  });

  it('allows officer to generate underwriting memo in pipeline', async () => {
    const phaseId = 'phase-1';
    const loanId = 'loan-1';
    const baseLoan = {
      id: loanId,
      borrowerName: 'Memo Borrower',
      conversationId: null,
      loanType: 'Home Loan',
      loanAmount: '250000',
      catalogProductCode: 'HL-PUR-001',
      currentPhaseId: phaseId,
      status: 'draft',
      documentChecklist: {
        productCode: 'HL-PUR-001',
        items: [{ name: 'PAN Card', status: 'missing', updatedAt: '2026-03-17T00:00:00.000Z' }],
        asOf: '2026-03-17T00:00:00.000Z',
      },
      underwritingMemo: null,
    };

    const loanWithMemo = {
      ...baseLoan,
      underwritingMemo: {
        loanId,
        productCode: 'HL-PUR-001',
        generatedAt: '2026-03-17T00:01:00.000Z',
        method: 'rules_v1',
        disclaimer: 'This is not a credit decision and does not imply approval.',
        flags: ['Credit score not provided'],
        nextActions: ['Collect credit score / bureau range'],
        sections: [{ title: 'Executive Summary', bullets: ['Scope: rules-based'] }],
      },
    };

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      const method = (init?.method || 'GET').toUpperCase();

      if (url.endsWith('/api/phases') && method === 'GET') {
        return new Response(JSON.stringify([{ id: phaseId, name: 'Lead & Inquiry', sortOrder: 1, isActive: true }]), { status: 200 });
      }
      if (url.endsWith('/api/loans') && method === 'GET') {
        return new Response(JSON.stringify([baseLoan]), { status: 200 });
      }
      // Pipeline view also loads conversations in the background for cross-linking.
      if (url.endsWith('/api/conversations') && method === 'GET') {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.endsWith(`/api/loans/${loanId}/underwriting-memo`) && method === 'POST') {
        return new Response(JSON.stringify(loanWithMemo), { status: 200 });
      }
      return new Response('not found', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    renderApp(['/pipeline']);

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'officer' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await screen.findByRole('heading', { name: 'Pipeline' });
    await screen.findByTestId(`officer-hold-row-${loanId}`);

    fireEvent.click(screen.getByTestId(`officer-hold-row-${loanId}`));
    fireEvent.click(screen.getByTestId('loan-generate-memo-button'));
    await screen.findByText('Underwriting memo');
    expect(screen.getByText(/not a credit decision/i)).toBeInTheDocument();
  });
});
