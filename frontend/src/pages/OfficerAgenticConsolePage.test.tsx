import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom/vitest';
import OfficerAgenticConsolePage from './OfficerAgenticConsolePage';

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('OfficerAgenticConsolePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders empty state when no sessions exist', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url);
      if (u.includes('/api/officer/agentic/sessions')) return new Response(JSON.stringify([]), { status: 200 });
      return new Response('not found', { status: 404 });
    }));

    renderWithClient(<OfficerAgenticConsolePage />);
    expect(screen.getByText('Agentic Console')).toBeInTheDocument();
    expect(await screen.findByText('No agentic sessions found yet.')).toBeInTheDocument();
  });

  it('selects a session and loads details', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url);
      if (u.endsWith('/api/officer/agentic/sessions')) {
        return new Response(
          JSON.stringify([
            {
              sessionId: 's-1',
              applicationId: null,
              mode: 'intake',
              stage: 'capture_context',
              borrowerName: 'Ada',
              requiresManualReview: false,
              escalationNeeded: false,
              stpStatus: null,
              updatedAt: new Date().toISOString(),
              createdAt: new Date().toISOString(),
            },
          ]),
          { status: 200 },
        );
      }
      if (u.includes('/api/officer/agentic/sessions/s-1/messages')) return new Response(JSON.stringify([{ role: 'user', content: 'hello' }]), { status: 200 });
      if (u.includes('/api/officer/agentic/sessions/s-1')) return new Response(JSON.stringify({ sessionId: 's-1', mode: 'intake', stage: 'capture_context', borrowerName: 'Ada', requiresManualReview: false, escalationNeeded: false, stpStatus: null, updatedAt: null, createdAt: null }), { status: 200 });
      return new Response('not found', { status: 404 });
    }));

    renderWithClient(<OfficerAgenticConsolePage />);
    expect(await screen.findByText('Ada')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('agentic-session-s-1'));
    expect(await screen.findByText('Conversation transcript')).toBeInTheDocument();
    expect(await screen.findByText('hello')).toBeInTheDocument();
  });
});

