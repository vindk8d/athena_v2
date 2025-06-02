import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { signInWithEmail, signUpWithEmail, signInWithOAuth } from '@/utils/supabase';
import { AuthForm } from '@/components/AuthForm';

// Mock Supabase auth functions
jest.mock('@/utils/supabase', () => ({
  signInWithEmail: jest.fn(),
  signUpWithEmail: jest.fn(),
  signInWithOAuth: jest.fn(),
}));

describe('Authentication Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should handle email/password sign in', async () => {
    const mockSignIn = signInWithEmail as jest.Mock;
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: '123' } }, error: null });

    render(<AuthForm />);

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Verify the sign in function was called
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });

  it('should handle email/password sign up', async () => {
    const mockSignUp = signUpWithEmail as jest.Mock;
    mockSignUp.mockResolvedValueOnce({ data: { user: { id: '123' } }, error: null });

    render(<AuthForm />);

    // Switch to sign up mode
    fireEvent.click(screen.getByText(/create an account/i));

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign up/i }));

    // Verify the sign up function was called
    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });

  it('should handle OAuth sign in', async () => {
    const mockOAuthSignIn = signInWithOAuth as jest.Mock;
    mockOAuthSignIn.mockResolvedValueOnce({ data: { url: 'https://oauth.example.com' }, error: null });

    render(<AuthForm />);

    // Click OAuth button
    fireEvent.click(screen.getByRole('button', { name: /sign in with google/i }));

    // Verify the OAuth sign in function was called
    await waitFor(() => {
      expect(mockOAuthSignIn).toHaveBeenCalledWith('google');
    });
  });

  it('should display error messages', async () => {
    const mockSignIn = signInWithEmail as jest.Mock;
    mockSignIn.mockResolvedValueOnce({ data: null, error: { message: 'Invalid credentials' } });

    render(<AuthForm />);

    // Fill in the form
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'wrongpassword' },
    });

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });
}); 