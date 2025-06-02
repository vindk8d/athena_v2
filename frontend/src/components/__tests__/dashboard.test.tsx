import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { supabase } from '@/utils/supabase';
import Dashboard from '@/components/Dashboard';

// Mock Supabase client with table-specific logic
jest.mock('@/utils/supabase', () => {
  const mockUserDetails = {
    user_id: 'test-user-id',
    working_hours_start: '09:00',
    working_hours_end: '17:00',
    meeting_duration: 30,
    buffer_time: 15,
  };
  const mockContacts = [
    {
      id: '1',
      name: 'John Doe',
      email: 'john@example.com',
      telegram_id: '123456',
      created_at: '2024-03-20T10:00:00Z',
      messages: [
        {
          id: '1',
          content: 'Hello',
          created_at: '2024-03-20T10:00:00Z',
        },
      ],
    },
  ];
  let contactsData = mockContacts;
  let userDetailsData = mockUserDetails;
  let contactsError = null;
  let userDetailsError = null;

  return {
    supabase: {
      from: jest.fn((table: string) => {
        if (table === 'user_details') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                single: jest.fn(() => Promise.resolve({ data: userDetailsData, error: userDetailsError }))
              }))
            }))
          };
        }
        if (table === 'contacts') {
          return {
            select: jest.fn(() => ({
              order: jest.fn(() => ({
                limit: jest.fn(() => Promise.resolve({ data: contactsData, error: contactsError }))
              }))
            }))
          };
        }
        // Default fallback
        return {
          select: jest.fn(() => ({
            eq: jest.fn(() => ({
              single: jest.fn(() => Promise.resolve({ data: null, error: null }))
            }))
          }))
        };
      }),
      channel: jest.fn(() => ({
        on: jest.fn(() => ({
          subscribe: jest.fn(() => ({
            unsubscribe: jest.fn()
          }))
        }))
      }))
    }
  };
});

describe('Dashboard Component', () => {
  const mockContacts = [
    {
      id: '1',
      name: 'John Doe',
      email: 'john@example.com',
      telegram_id: '123456',
      created_at: '2024-03-20T10:00:00Z',
      messages: [
        {
          id: '1',
          content: 'Hello',
          created_at: '2024-03-20T10:00:00Z',
        },
      ],
    },
  ];

  const mockUserDetails = {
    user_id: 'test-user-id',
    working_hours_start: '09:00',
    working_hours_end: '17:00',
    meeting_duration: 30,
    buffer_time: 15,
  };

  const mockUserId = 'test-user-id';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should load and display recent contacts', async () => {
    render(<Dashboard userId={mockUserId} />);

    // Wait for contacts to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Verify contact details are displayed
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('123456')).toBeInTheDocument();
  });

  it('should handle contact selection and display messages', async () => {
    render(<Dashboard userId={mockUserId} />);

    // Wait for contacts to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Click on a contact
    fireEvent.click(screen.getByText('John Doe'));

    // Verify messages are loaded
    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });
  });

  it('should handle time filter changes', async () => {
    render(<Dashboard userId={mockUserId} />);

    // Wait for contacts to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Change time filter to "Today"
    fireEvent.click(screen.getByText('Today'));

    // Verify contacts are filtered
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
  });

  it('should handle error states', async () => {
    // Patch the mock to return an error for contacts
    const { supabase } = require('@/utils/supabase');
    supabase.from.mockImplementation((table: string) => {
      if (table === 'user_details') {
        return {
          select: jest.fn(() => ({
            eq: jest.fn(() => ({
              single: jest.fn(() => Promise.resolve({ data: mockUserDetails, error: null }))
            }))
          }))
        };
      }
      if (table === 'contacts') {
        return {
          select: jest.fn(() => ({
            order: jest.fn(() => ({
              limit: jest.fn(() => Promise.resolve({ data: null, error: { message: 'Failed to load contacts' } }))
            }))
          }))
        };
      }
      return {
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            single: jest.fn(() => Promise.resolve({ data: null, error: null }))
          }))
        }))
      };
    });

    render(<Dashboard userId={mockUserId} />);

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/failed to load contacts/i)).toBeInTheDocument();
    });
  });

  it('should handle empty states', async () => {
    // Patch the mock to return empty contacts
    const { supabase } = require('@/utils/supabase');
    supabase.from.mockImplementation((table: string) => {
      if (table === 'user_details') {
        return {
          select: jest.fn(() => ({
            eq: jest.fn(() => ({
              single: jest.fn(() => Promise.resolve({ data: mockUserDetails, error: null }))
            }))
          }))
        };
      }
      if (table === 'contacts') {
        return {
          select: jest.fn(() => ({
            order: jest.fn(() => ({
              limit: jest.fn(() => Promise.resolve({ data: [], error: null }))
            }))
          }))
        };
      }
      return {
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            single: jest.fn(() => Promise.resolve({ data: null, error: null }))
          }))
        }))
      };
    });

    render(<Dashboard userId={mockUserId} />);

    // Verify empty state message is displayed
    await waitFor(() => {
      expect(screen.getByText(/no contacts found/i)).toBeInTheDocument();
    });
  });
}); 