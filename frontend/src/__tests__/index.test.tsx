import { render, screen } from '@testing-library/react';
import Home from '../index';

describe('Home Page', () => {
  it('renders the main heading', () => {
    render(<Home />);
    const heading = screen.getByRole('heading', { name: /athena digital executive assistant/i });
    expect(heading).toBeInTheDocument();
  });

  it('renders the welcome message', () => {
    render(<Home />);
    const welcomeMessage = screen.getByText(
      /welcome to your ai-powered contact and meeting manager/i,
    );
    expect(welcomeMessage).toBeInTheDocument();
  });

  it('renders the login link', () => {
    render(<Home />);
    const loginLink = screen.getByRole('link', { name: /login to dashboard/i });
    expect(loginLink).toBeInTheDocument();
    expect(loginLink).toHaveAttribute('href', '/login');
  });
});
