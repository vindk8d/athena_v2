import { createClient } from '@supabase/supabase-js';
import { Database } from '@/types/supabase';

if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_URL');
}
if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_ANON_KEY');
}

export const supabase = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: 'pkce',
    },
    realtime: {
      params: {
        eventsPerSecond: 10,
      },
    },
  },
);

// Auth helper functions
export const signInWithEmail = async (email: string, password: string) => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  return { data, error };
};

export const signUpWithEmail = async (email: string, password: string) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  });
  return { data, error };
};

export const signInWithOAuth = async (provider: 'google' | 'github') => {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  return { data, error };
};

export const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  return { error };
};

// Data access functions
export const getUserPreferences = async (userId: string) => {
  const { data, error } = await supabase
    .from('user_details')
    .select('*')
    .eq('user_id', userId)
    .single();
  return { data, error };
};

export const updateUserPreferences = async (userId: string, preferences: Partial<UserDetails>) => {
  const { data, error } = await supabase
    .from('user_details')
    .update(preferences)
    .eq('user_id', userId)
    .select()
    .single();
  return { data, error };
};

export const getRecentContacts = async (limit = 10) => {
  const { data, error } = await supabase
    .from('contacts')
    .select('*, messages(*)')
    .order('created_at', { ascending: false })
    .limit(limit);
  return { data, error };
};

export const getContactMessages = async (contactId: string, limit = 50) => {
  const { data, error } = await supabase
    .from('messages')
    .select('*')
    .eq('contact_id', contactId)
    .order('created_at', { ascending: false })
    .limit(limit);
  return { data, error };
};

// Realtime subscriptions
export const subscribeToNewMessages = (callback: (payload: Message) => void) => {
  return supabase
    .channel('messages')
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' }, (payload) => {
      callback(payload.new as Message);
    })
    .subscribe();
};

export const subscribeToContactUpdates = (callback: (payload: Contact) => void) => {
  return supabase
    .channel('contacts')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'contacts' }, (payload) => {
      callback(payload.new as Contact);
    })
    .subscribe();
};

// Types
export interface UserDetails {
  id: string;
  user_id: string;
  working_hours_start: string | null;
  working_hours_end: string | null;
  meeting_duration: number | null;
  buffer_time: number | null;
  telegram_id: string | null;
  created_at: string;
  updated_at: string;
  metadata?: {
    working_days?: {
      monday: boolean;
      tuesday: boolean;
      wednesday: boolean;
      thursday: boolean;
      friday: boolean;
      saturday: boolean;
      sunday: boolean;
    };
    timezone?: string;
  };
}

export type Contact = Database['public']['Tables']['contacts']['Row'];
export type Message = Database['public']['Tables']['messages']['Row'];

export const handleRealtimeSubscription = (): void => {
  // Implementation here
};

export const handleRealtimeError = (): void => {
  // Implementation here
};

// New function to fetch data from the Python backend API
export const fetchBackendData = async () => {
  const response = await fetch('https://athena-v2-ikdq.onrender.com/health');
  if (!response.ok) {
    throw new Error('Failed to fetch data from backend');
  }
  return response.json();
};
