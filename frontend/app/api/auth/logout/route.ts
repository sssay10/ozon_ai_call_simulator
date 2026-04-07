import { NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

const BACKEND_SERVICE_URL = process.env.BACKEND_SERVICE_URL ?? process.env.AUTH_SERVICE_URL;

export const revalidate = 0;

export async function POST() {
  try {
    if (BACKEND_SERVICE_URL) {
      await fetch(new URL('/api/auth/logout', BACKEND_SERVICE_URL).toString(), {
        method: 'POST',
        cache: 'no-store',
      });
    }

    const response = NextResponse.json({ status: 'ok' }, { headers: { 'Cache-Control': 'no-store' } });
    response.cookies.set(AUTH_COOKIE_NAME, '', {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: 0,
    });
    return response;
  } catch (error) {
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('Unknown error', { status: 500 });
  }
}
