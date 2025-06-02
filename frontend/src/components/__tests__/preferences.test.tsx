import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { supabase } from '@/utils/supabase';
import PreferencesPanel from '@/components/PreferencesPanel';

// Mock Supabase client
jest.mock('@/utils/supabase', () => ({
  supabase: {
    from: jest.fn(() => ({
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      single: jest.fn(),
      update: jest.fn().mockReturnThis(),
    })),
  },
}));

describe('PreferencesPanel Component', () => {
  const mockUserId = 'test-user-id';
  const mockPreferences = {
    id: '1',
    user_id: mockUserId,
    working_hours_start: '09:00',
    working_hours_end: '17:00',
    meeting_duration: 60,
    buffer_time: 15,
    telegram_id: null,
    created_at: '2024-03-20T10:00:00Z',
    updated_at: '2024-03-20T10:00:00Z',
    metadata: {
      working_days: {
        monday: true,
        tuesday: true,
        wednesday: true,
        thursday: true,
        friday: true,
        saturday: false,
        sunday: false,
      },
      timezone: 'America/New_York',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (supabase.from as jest.Mock).mockImplementation(() => ({
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      single: jest.fn().mockResolvedValue({ data: mockPreferences, error: null }),
      update: jest.fn().mockReturnThis(),
    }));
  });

  it('should load and display user preferences', async () => {
    render(<PreferencesPanel userId={mockUserId} />);

    // Wait for preferences to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('09:00')).toBeInTheDocument();
      expect(screen.getByDisplayValue('17:00')).toBeInTheDocument();
    });

    // Verify other preferences are displayed
    expect(screen.getByText('1 hour')).toBeInTheDocument();
    expect(screen.getByText('15 minutes')).toBeInTheDocument();
  });

  it('should handle working hours changes', async () => {
    render(<PreferencesPanel userId={mockUserId} />);

    // Wait for preferences to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('09:00')).toBeInTheDocument();
    });

    // Change start time
    fireEvent.change(screen.getByLabelText(/start time/i), {
      target: { value: '10:00' },
    });

    // Save changes
    fireEvent.click(screen.getByRole('button', { name: /save preferences/i }));

    // Verify update was called
    await waitFor(() => {
      expect(supabase.from).toHaveBeenCalledWith('user_details');
    });
  });

  it('should handle working days changes', async () => {
    render(<PreferencesPanel userId={mockUserId} />);

    // Wait for preferences to load
    await waitFor(() => {
      expect(screen.getByLabelText(/monday/i)).toBeInTheDocument();
    });

    // Toggle Saturday
    fireEvent.click(screen.getByLabelText(/saturday/i));

    // Save changes
    fireEvent.click(screen.getByRole('button', { name: /save preferences/i }));

    // Verify update was called
    await waitFor(() => {
      expect(supabase.from).toHaveBeenCalledWith('user_details');
    });
  });

  it('should handle timezone changes', async () => {
    render(<PreferencesPanel userId={mockUserId} />);

    // Wait for preferences to load
    await waitFor(() => {
      expect(screen.getByText('America/New_York')).toBeInTheDocument();
    });

    // Change timezone
    fireEvent.click(screen.getByText('America/New_York'));
    fireEvent.click(screen.getByText('America/Los_Angeles'));

    // Save changes
    fireEvent.click(screen.getByRole('button', { name: /save preferences/i }));

    // Verify update was called
    await waitFor(() => {
      expect(supabase.from).toHaveBeenCalledWith('user_details');
    });
  });

  it('should handle error states', async () => {
    (supabase.from as jest.Mock).mockImplementation(() => ({
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      single: jest.fn().mockResolvedValue({ data: null, error: { message: 'Failed to load preferences' } }),
    }));

    render(<PreferencesPanel userId={mockUserId} />);

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/failed to load preferences/i)).toBeInTheDocument();
    });
  });
}); 