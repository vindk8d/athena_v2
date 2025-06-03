import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { supabase } from '@/utils/supabase';

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const handleAuthCallback = async () => {
      console.log('Auth callback page: Starting auth callback handling');
      console.log('Auth callback page: URL params:', router.query);

      try {
        // First check if we have a session
        const {
          data: { session },
          error: sessionError,
        } = await supabase.auth.getSession();
        console.log('Auth callback page: Initial session check:', {
          hasSession: !!session,
          error: sessionError,
          sessionData: session
            ? {
                user: session.user?.email,
                expiresAt: session.expires_at,
                accessToken: !!session.access_token,
              }
            : null,
        });

        if (sessionError) {
          console.error('Auth callback page: Error during session check:', sessionError);
          router.push('/auth/login');
          return;
        }

        // If no session, try to get the session from the URL
        if (!session) {
          console.log('Auth callback page: No session found, checking URL for auth code');
          const {
            data: { session: newSession },
            error: urlError,
          } = await supabase.auth.getSession();
          console.log('Auth callback page: URL session check:', {
            hasSession: !!newSession,
            error: urlError,
            sessionData: newSession
              ? {
                  user: newSession.user?.email,
                  expiresAt: newSession.expires_at,
                  accessToken: !!newSession.access_token,
                }
              : null,
          });

          if (urlError) {
            console.error('Auth callback page: Error getting session from URL:', urlError);
            router.push('/auth/login');
            return;
          }

          if (!newSession) {
            console.log('Auth callback page: No session found in URL, redirecting to login');
            router.push('/auth/login');
            return;
          }
        }

        console.log('Auth callback page: Session found, redirecting to dashboard');
        router.push('/dashboard');
      } catch (err) {
        console.error('Auth callback page: Unexpected error:', err);
        router.push('/auth/login');
      }
    };

    handleAuthCallback();
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
    </div>
  );
}
