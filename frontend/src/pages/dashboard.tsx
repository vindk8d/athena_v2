import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { supabase } from '@/utils/supabase';
import Dashboard from '@/components/Dashboard';

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const {
          data: { session },
          error,
        } = await supabase.auth.getSession();

        console.log('[DashboardPage] Supabase session:', session);
        console.log('[DashboardPage] Supabase session error:', error);

        if (error || !session) {
          console.log('[DashboardPage] No session or error, redirecting to /auth/login');
          router.replace('/auth/login');
          return;
        }

        if (!session.user || !session.user.id) {
          console.error(
            '[DashboardPage] Session present but user or user.id is missing:',
            session.user,
          );
          setError('Authenticated session is missing user information.');
          setLoading(false);
          return;
        }

        setUserId(session.user.id);
        setLoading(false);
      } catch (err) {
        console.error('[DashboardPage] Unexpected error:', err);
        setError('An unexpected error occurred. Please try again.');
        setLoading(false);
      }
    };

    checkSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('[DashboardPage] Auth state changed:', { event, session });
      if (event === 'SIGNED_OUT') {
        router.replace('/auth/login');
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  console.log('[DashboardPage] Render state:', { loading, userId, error });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  if (!userId) {
    if (typeof window !== 'undefined') {
      console.error('[DashboardPage] userId is missing after loading. Redirecting to /auth/login');
      router.replace('/auth/login');
    }
    return null;
  }

  console.log('[DashboardPage] Rendering Dashboard with userId:', userId);
  return <Dashboard userId={userId} />;
}
