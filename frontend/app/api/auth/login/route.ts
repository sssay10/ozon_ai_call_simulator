import { NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

const BACKEND_SERVICE_URL = process.env.BACKEND_SERVICE_URL ?? process.env.AUTH_SERVICE_URL;

export const revalidate = 0;

export async function POST(req: Request) {
  try {
    if (!BACKEND_SERVICE_URL) {
      throw new Error('BACKEND_SERVICE_URL is not defined');
    }

    const body = await req.json();
    const response = await fetch(new URL('/api/auth/login', BACKEND_SERVICE_URL).toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    const text = await response.text();
    if (!response.ok) {
      return new NextResponse(text, { status: response.status });
    }

    const data = JSON.parse(text) as {
      access_token: string;
      user: { user_id: string; email: string; role: string };
    };
    const nextResponse = NextResponse.json(data.user, {
      headers: { 'Cache-Control': 'no-store' },
    });
    nextResponse.cookies.set(AUTH_COOKIE_NAME, data.access_token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: 60 * 60 * 24,
    });
    return nextResponse;
  } catch (error) {
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('Unknown error', { status: 500 });
  }
}
