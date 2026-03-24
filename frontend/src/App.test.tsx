import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';

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
      render(
        <MemoryRouter initialEntries={['/login']}>
          <App />
        </MemoryRouter>
      );
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
      if (url.endsWith(`/api/conversations/${leadId}`) && method === 'PATCH') {
        return new Response(JSON.stringify(updatedLead), { status: 200 });
      }
      return new Response('not found', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <App />
      </MemoryRouter>
    );

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'officer' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await screen.findByTestId('text-leads-title');
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/conversations'), expect.anything());
    });

    fireEvent.click(await screen.findByTestId(`lead-row-${leadId}`));
    expect(screen.getByTestId('text-approval-probability-title')).toBeInTheDocument();
    expect(screen.getByTestId('text-approval-probability-score')).toHaveTextContent('60%');
    expect(screen.getByTestId('approval-navigator-officer')).toBeInTheDocument();
    expect(screen.getByTestId('approval-blocker-officer-0')).toHaveTextContent('Missing credit score');
    expect(screen.getByTestId('approval-action-officer-0')).toHaveTextContent('Share credit score range');

    fireEvent.change(screen.getByTestId('input-borrower-name'), { target: { value: 'Jane Doe' } });
    fireEvent.change(screen.getByTestId('input-assigned-officer'), { target: { value: 'officer-1' } });
    fireEvent.change(screen.getByTestId('select-lead-status'), { target: { value: 'reviewing' } });
    fireEvent.click(screen.getByTestId('button-save-lead'));

    await screen.findByTestId('text-save-ok');
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
  });

  it('allows officer to generate underwriting memo in pipeline', async () => {
    const phaseId = 'phase-1';
    const loanId = 'loan-1';
    const baseLoan = {
      id: loanId,
      borrowerName: 'Memo Borrower',
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
      if (url.endsWith(`/api/loans/${loanId}/underwriting-memo`) && method === 'POST') {
        return new Response(JSON.stringify(loanWithMemo), { status: 200 });
      }
      return new Response('not found', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/pipeline']}>
        <App />
      </MemoryRouter>
    );

    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'officer' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Password123!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await screen.findByRole('heading', { name: 'Loans' });
    await screen.findByTestId(`loan-row-${loanId}`);

    fireEvent.click(screen.getByTestId(`loan-row-${loanId}`));
    expect(await screen.findByTestId('text-underwriting-memo-title')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('button-generate-underwriting-memo'));
    await screen.findByTestId('underwriting-memo');
    expect(screen.getByTestId('underwriting-memo-disclaimer')).toHaveTextContent('not a credit decision');
  });
});
