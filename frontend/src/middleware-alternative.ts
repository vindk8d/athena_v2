import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(req: NextRequest) {
  const pathname = req.nextUrl.pathname;
  
  // Skip middleware for auth pages, Next.js internals, API routes, static files
  if (
    pathname.startsWith('/auth/') ||
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
    const { data: { session } } = await supabase.auth.getSession();

    // If session exists, clear redirect count and allow access
    if (session) {
      res.cookies.delete('redirectCount');
      return res;
    }

    // No session - check redirect count from cookies
    const redirectCount = parseInt(req.cookies.get('redirectCount')?.value || '0');
    
    if (redirectCount >= 3) {
      const errorUrl = req.nextUrl.clone();
      errorUrl.pathname = '/auth/redirect-error';
      const errorResponse = NextResponse.redirect(errorUrl);
      errorResponse.cookies.delete('redirectCount');
      return errorResponse;
    }

    // Increment redirect count and redirect to login
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = '/auth/login';
    loginUrl.searchParams.set('redirectedFrom', pathname);
    
    const redirectResponse = NextResponse.redirect(loginUrl);
    redirectResponse.cookies.set('redirectCount', String(redirectCount + 1), {
      maxAge: 60 * 5, // 5 minutes
      httpOnly: true,
      sameSite: 'lax'
    });
    
    return redirectResponse;

  } catch (error) {
    // On error, redirect to login with redirect count
    const redirectCount = parseInt(req.cookies.get('redirectCount')?.value || '0');
    
    if (redirectCount >= 3) {
      const errorUrl = req.nextUrl.clone();
      errorUrl.pathname = '/auth/redirect-error';
      const errorResponse = NextResponse.redirect(errorUrl);
      errorResponse.cookies.delete('redirectCount');
      return errorResponse;
    }
    
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = '/auth/login';
    
    const redirectResponse = NextResponse.redirect(loginUrl);
    redirectResponse.cookies.set('redirectCount', String(redirectCount + 1), {
      maxAge: 60 * 5, // 5 minutes
      httpOnly: true,
      sameSite: 'lax'
    });
    
    return redirectResponse;
  }
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}; 