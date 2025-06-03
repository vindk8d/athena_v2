import { useEffect, useState, useRef } from 'react';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from '@/utils/supabase';
import { useRouter } from 'next/router';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Subscription } from '@supabase/supabase-js';

export default function LoginPage() {
  const router = useRouter();
  const [redirectTo, setRedirectTo] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSigningIn, setIsSigningIn] = useState(false);
  const redirectAttempts = useRef(0);
  const isRedirecting = useRef(false);
  const authStateChangeSubscription = useRef<Subscription | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const callbackUrl = `${window.location.origin}/auth/callback`;
      console.log('Login page: Setting redirect URL:', callbackUrl);
      setRedirectTo(callbackUrl);
    }
  }, []);

  // Handle manual navigation to dashboard
  const navigateToDashboard = () => {
    if (isRedirecting.current) return;
    console.log('Login page: Manually navigating to dashboard');
    isRedirecting.current = true;
    router.replace('/dashboard');
  };

  useEffect(() => {
    let mounted = true;

    // Check if we're already authenticated
    const checkSession = async () => {
      if (!mounted || isRedirecting.current) return;
      console.log('Login page: Checking existing session');
      try {
        const {
          data: { session },
          error,
        } = await supabase.auth.getSession();
        console.log('Login page: Session check result:', {
          hasSession: !!session,
          error,
          sessionData: session
            ? {
                user: session.user?.email,
                expiresAt: session.expires_at,
                accessToken: !!session.access_token,
              }
            : null,
        });

        if (session && session.user) {
          // Validate session is not expired
          const now = Math.floor(Date.now() / 1000);
          if (session.expires_at && session.expires_at < now) {
            console.log('Login page: Session expired, signing out');
            await supabase.auth.signOut();
            setError('Your session has expired. Please sign in again.');
            setIsLoading(false);
            return;
          }

          // Prevent redirect loops
          if (redirectAttempts.current >= 3) {
            console.log('Login page: Too many redirect attempts, stopping');
            setError('Too many redirect attempts. Please try refreshing the page.');
            setIsLoading(false);
            return;
          }

          console.log('Login page: Session found, redirecting to dashboard');
          isRedirecting.current = true;
          redirectAttempts.current += 1;
          router.replace('/dashboard');
          return;
        }
      } catch (err) {
        console.error('Login page: Error checking session:', err);
        setError('Error checking authentication status. Please try again.');
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    // Add a timeout to ensure the page becomes interactive even if there's an issue
    const timeoutId = setTimeout(() => {
      if (mounted) {
        console.log('Login page: Loading timeout reached, forcing interactive state');
        setIsLoading(false);
      }
    }, 3000); // 3 second timeout

    checkSession();

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (!mounted || isRedirecting.current) return;

      console.log('Login page: Auth state changed:', {
        event,
        hasSession: !!session,
        sessionData: session
          ? {
              user: session.user?.email,
              expiresAt: session.expires_at,
              accessToken: !!session.access_token,
            }
          : null,
      });

      if (event === 'SIGNED_IN' && session) {
        // Prevent redirect loops
        if (redirectAttempts.current >= 3) {
          console.log('Login page: Too many redirect attempts, stopping');
          setError('Too many redirect attempts. Please try refreshing the page.');
          return;
        }

        console.log('Login page: User signed in, redirecting to dashboard');
        isRedirecting.current = true;
        redirectAttempts.current += 1;
        setIsSigningIn(false);
        router.replace('/dashboard');
      } else if (event === 'SIGNED_OUT') {
        console.log('Login page: User signed out');
        isRedirecting.current = false;
        redirectAttempts.current = 0;
        setIsSigningIn(false);
      }
    });

    authStateChangeSubscription.current = subscription;

    return () => {
      mounted = false;
      clearTimeout(timeoutId);
      if (authStateChangeSubscription.current) {
        authStateChangeSubscription.current.unsubscribe();
      }
    };
  }, [router]);

  const handleSignOut = async () => {
    try {
      setIsSigningIn(true);
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      console.log('Login page: Signed out successfully');
      // Reset redirect attempts
      redirectAttempts.current = 0;
      isRedirecting.current = false;
      setIsSigningIn(false);
    } catch (err) {
      console.error('Login page: Error signing out:', err);
      setError('Error signing out. Please try again.');
      setIsSigningIn(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Welcome back</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          )}
          <Auth
            supabaseClient={supabase}
            appearance={{ theme: ThemeSupa }}
            theme="light"
            providers={['google']}
            redirectTo={redirectTo}
            onlyThirdPartyProviders
          />
          <div className="mt-4 flex justify-center">
            <Button
              variant="outline"
              onClick={handleSignOut}
              className="text-sm text-gray-600"
              disabled={isSigningIn}
            >
              {isSigningIn ? 'Signing Out...' : 'Sign Out'}
            </Button>
          </div>
          <div className="mt-4 flex justify-center">
            <Button
              variant="outline"
              onClick={navigateToDashboard}
              className="text-sm text-gray-600"
              disabled={isSigningIn}
            >
              Go to Dashboard
            </Button>
          </div>
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-gray-600 mt-4">
            Don&apos;t have an account?{' '}
            <Link href="/auth/signup" className="text-blue-600 hover:text-blue-700">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
