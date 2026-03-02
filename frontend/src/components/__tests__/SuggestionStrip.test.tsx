import { render, screen } from '@testing-library/react';
import { SuggestionStrip } from '../SuggestionStrip';
import { vi, describe, it, expect } from 'vitest';
import '@testing-library/jest-dom';

describe('SuggestionStrip', () => {
  const mockSuggestions = [
    { label: 'Test User (Antigua)', text: 'My name is Test User...' },
    { label: 'Jane Doe (Grenada)', text: 'I am Jane...' }
  ];

  it('renders nothing initially when suggestions are empty', () => {
    const { container } = render(<SuggestionStrip suggestions={[]} onSelect={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('displays suggestions when provided', () => {
    render(<SuggestionStrip suggestions={mockSuggestions} onSelect={() => {}} />);

    expect(screen.getByText('Test User (Antigua)')).toBeInTheDocument();
    expect(screen.getByText('Jane Doe (Grenada)')).toBeInTheDocument();
  });

  it('calls onSelect when a suggestion is clicked', () => {
    const handleSelect = vi.fn();
    render(<SuggestionStrip suggestions={mockSuggestions} onSelect={handleSelect} />);

    screen.getByText('Test User (Antigua)').click();
    expect(handleSelect).toHaveBeenCalledWith('My name is Test User...');
  });
});
