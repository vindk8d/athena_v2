import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(req: NextRequest) {
  // Get the current pathname and initialize redirect count from URL params
  const pathname = req.nextUrl.pathname;
  const redirectCount = parseInt(req.nextUrl.searchParams.get('redirectCount') || '0');

  // Skip middleware for Next.js internals, API routes, static files
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/api/') ||
    pathname === '/favicon.ico' ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Only protect dashboard routes
  if (!pathname.startsWith('/dashboard')) {
    return NextResponse.next();
  }

  // Check session for dashboard routes
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });

  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    console.log('MIDDLEWARE SESSION:', session, req.cookies);

    // If session exists, allow access
    if (session) {
      return res;
    }

    // No session - count redirects
    if (redirectCount >= 3) {
      const errorUrl = req.nextUrl.clone();
      errorUrl.pathname = '/auth/redirect-error';
      errorUrl.searchParams.delete('redirectCount');
      return NextResponse.redirect(errorUrl);
    }

    // Otherwise, increment redirectCount and redirect to login
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = '/auth/login';
    loginUrl.searchParams.set('redirectedFrom', pathname);
    loginUrl.searchParams.set('redirectCount', String(redirectCount + 1));
    return NextResponse.redirect(loginUrl);
  } catch (error) {
    // On error, redirect to login with redirectCount
    if (redirectCount >= 3) {
      const errorUrl = req.nextUrl.clone();
      errorUrl.pathname = '/auth/redirect-error';
      errorUrl.searchParams.delete('redirectCount');
      return NextResponse.redirect(errorUrl);
    }
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = '/auth/login';
    loginUrl.searchParams.set('redirectCount', String(redirectCount + 1));
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - auth (authentication pages)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|auth).*)',
  ],
};
