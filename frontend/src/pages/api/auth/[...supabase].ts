import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function GET(request: NextRequest) {
  console.log('Auth API: Handling GET request');
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');
  console.log('Auth API: Auth code present:', !!code);

  if (code) {
    const cookieStore = cookies();
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore });

    try {
      console.log('Auth API: Attempting to exchange code for session');
      const { data, error } = await supabase.auth.exchangeCodeForSession(code);
      console.log('Auth API: Exchange result:', { success: !!data, error });

      if (error) {
        console.error('Auth API: Error exchanging code:', error);
        return NextResponse.redirect(new URL('/auth/login', request.url));
      }

      console.log('Auth API: Successfully exchanged code, redirecting to dashboard');
      return NextResponse.redirect(new URL('/dashboard', request.url));
    } catch (error) {
      console.error('Auth API: Unexpected error during code exchange:', error);
      return NextResponse.redirect(new URL('/auth/login', request.url));
    }
  }

  console.log('Auth API: No code present, redirecting to login');
  return NextResponse.redirect(new URL('/auth/login', request.url));
}

export async function POST(request: NextRequest) {
  console.log('Auth API: Handling POST request');
  const cookieStore = cookies();
  const supabase = createRouteHandlerClient({ cookies: () => cookieStore });

  try {
    const formData = await request.json();
    const { email, password } = formData;
    console.log('Auth API: Attempting sign in for email:', email);

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    console.log('Auth API: Sign in result:', { success: !!data, error });

    if (error) {
      console.error('Auth API: Sign in error:', error);
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    console.log('Auth API: Sign in successful');
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Auth API: Unexpected error in POST handler:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
