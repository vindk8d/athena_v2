import { useEffect, useState } from 'react';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from '@/utils/supabase';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import Link from 'next/link';

export default function LoginPage() {
  const [redirectTo, setRedirectTo] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setRedirectTo(`${window.location.origin}/auth/callback`);
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Welcome back</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <Auth
            supabaseClient={supabase}
            appearance={{ theme: ThemeSupa }}
            providers={['google', 'github']}
            redirectTo={redirectTo}
            view="sign_in"
          />
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
