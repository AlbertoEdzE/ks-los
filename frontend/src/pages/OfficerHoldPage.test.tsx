import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import OfficerHoldPage from './OfficerHoldPage';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('OfficerHoldPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders empty state when no holds', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url);
      if (u.includes('/api/conversations')) return new Response(JSON.stringify([]), { status: 200 });
      if (u.includes('/api/loans')) return new Response(JSON.stringify([]), { status: 200 });
      return new Response('not found', { status: 404 });
    }));

    renderWithClient(<OfficerHoldPage />);
    expect(screen.getByText('Officer Hold')).toBeInTheDocument();

    // Wait for query resolution
    expect(await screen.findByText('No holds found.')).toBeInTheDocument();
  });

  it('shows lead holds when blockers exist', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url);
      if (u.includes('/api/conversations')) {
        return new Response(
          JSON.stringify([
            {
              id: 'c-1',
              borrowerName: 'Ada',
              status: 'active',
              chatRole: 'borrower',
              currentPhaseId: null,
              seriousnessScore: null,
              fitScore: null,
              intentSummary: null,
              approvalProbability: {
                probability: 0.4,
                band: 'low',
                topBlockers: [{ title: 'Missing credit score', detail: 'Credit score not provided yet.', severity: 'high' }],
                topActions: [{ title: 'Share credit score range', detail: 'Provide an estimated score.', impact: 'high' }],
                inputsUsed: {},
                method: 'heuristic_v1',
                asOf: new Date().toISOString(),
              },
              recommendedProducts: null,
              nextConversationAngle: null,
              assignedOfficer: null,
              createdAt: new Date().toISOString(),
            },
          ]),
          { status: 200 },
        );
      }
      if (u.includes('/api/loans')) return new Response(JSON.stringify([]), { status: 200 });
      return new Response('not found', { status: 404 });
    }));

    renderWithClient(<OfficerHoldPage />);
    expect(await screen.findByText('Ada')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('officer-hold-row-c-1'));
    expect(await screen.findByText('Approval Probability')).toBeInTheDocument();
    expect(screen.getByText('Top blockers')).toBeInTheDocument();
  });
});
