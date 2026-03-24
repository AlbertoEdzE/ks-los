import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BorrowerJourneyTracker } from '../BorrowerJourneyTracker';
import type { V2Message } from '../BorrowerJourneyTracker';
import '@testing-library/jest-dom/vitest';

const baseMessage = (overrides: Partial<V2Message>): V2Message => ({
  id: 'm1',
  conversationId: 'c1',
  role: 'assistant',
  content: 'Hello',
  createdAt: null,
  ...overrides,
});

describe('BorrowerJourneyTracker', () => {
  it('renders step 1 for empty messages', () => {
    render(<BorrowerJourneyTracker messages={[]} />);
    expect(screen.getByText(/Step 1 of 7/i)).toBeInTheDocument();
  });

  it('renders step 1 for messages without metadata', () => {
    const messages: V2Message[] = [
      baseMessage({ id: '1', role: 'user', content: 'Hello', metadata: undefined }),
      baseMessage({ id: '2', role: 'assistant', content: 'Hi there', metadata: undefined }),
    ];
    render(<BorrowerJourneyTracker messages={messages} />);
    expect(screen.getByText(/Step 1 of 7/i)).toBeInTheDocument();
  });

  it('derives step 3 from loan application success', () => {
    const messages: V2Message[] = [
      baseMessage({
        content: 'Application submitted',
        metadata: JSON.stringify({ loanApplication: { success: true, loanId: 'LOAN-001' } }),
      }),
    ];
    render(<BorrowerJourneyTracker messages={messages} />);
    expect(screen.getByText(/Step 3 of 7/i)).toBeInTheDocument();
  });

  it('derives step 5 from STP approval', () => {
    const messages: V2Message[] = [
      baseMessage({
        content: 'Approved!',
        metadata: JSON.stringify({ loanApplication: { stpApproved: true, approval: { rate: '8%', tenure: '20 years' } } }),
      }),
    ];
    render(<BorrowerJourneyTracker messages={messages} />);
    expect(screen.getByText(/Step 5 of 7/i)).toBeInTheDocument();
  });

  it('derives step 7 from STP completion with disbursement', () => {
    const messages: V2Message[] = [
      baseMessage({
        content: 'Funds disbursed!',
        metadata: JSON.stringify({ loanApplication: { stpCompleted: true, disbursement: { amount: '50000', reference: 'TXN-001' } } }),
      }),
    ];
    render(<BorrowerJourneyTracker messages={messages} />);
    expect(screen.getByText(/Step 7 of 7/i)).toBeInTheDocument();
  });

  it('derives step from phase name - disbursement', () => {
    render(<BorrowerJourneyTracker currentPhaseName="Disbursement" messages={[]} />);
    expect(screen.getByText(/Step 7 of 7/i)).toBeInTheDocument();
  });

  it('derives step from phase name - approval', () => {
    render(<BorrowerJourneyTracker currentPhaseName="Conditional Approval & Offer" messages={[]} />);
    expect(screen.getByText(/Step 5 of 7/i)).toBeInTheDocument();
  });

  it('derives step from phase name - document collection', () => {
    render(<BorrowerJourneyTracker currentPhaseName="Document Collection & KYC" messages={[]} />);
    expect(screen.getByText(/Step 3 of 7/i)).toBeInTheDocument();
  });

  it('derives step from phase name - application', () => {
    render(<BorrowerJourneyTracker currentPhaseName="Application Submission" messages={[]} />);
    expect(screen.getByText(/Step 2 of 7/i)).toBeInTheDocument();
  });

  it('uses metadata-derived step over phase name', () => {
    const messages: V2Message[] = [
      baseMessage({
        content: 'Application submitted',
        metadata: JSON.stringify({ loanApplication: { success: true } }),
      }),
    ];
    render(<BorrowerJourneyTracker currentPhaseName="Application Submission" messages={messages} />);
    expect(screen.getByText(/Step 3 of 7/i)).toBeInTheDocument();
  });
});
