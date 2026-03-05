import { render, screen } from '@testing-library/react';
import App from './App';
import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom';

describe('App', () => {
  it('renders login screen initially', () => {
    try {
      render(<App />);
      expect(screen.getByText('Login')).toBeInTheDocument();
    } catch (error) {
      console.error('App render failed:', error);
      throw error;
    }
  });
});
