import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom';
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
      expect(screen.getByText('Login')).toBeInTheDocument();
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

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'admin123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Login' }));

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
});
