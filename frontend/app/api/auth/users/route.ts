import { NextResponse } from 'next/server';
import { getAuthToken, getCurrentUser } from '@/lib/auth';

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL;

export const revalidate = 0;

export async function GET() {
  try {
    const currentUser = await getCurrentUser();
    const token = await getAuthToken();
    if (!currentUser || !token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }
    if (currentUser.role !== 'coach') {
      return new NextResponse('Forbidden', { status: 403 });
    }
    if (!AUTH_SERVICE_URL) {
      throw new Error('AUTH_SERVICE_URL is not defined');
    }

    const response = await fetch(new URL('/api/auth/users', AUTH_SERVICE_URL).toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: 'no-store',
    });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('Unknown error', { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const currentUser = await getCurrentUser();
    const token = await getAuthToken();
    if (!currentUser || !token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }
    if (currentUser.role !== 'coach') {
      return new NextResponse('Forbidden', { status: 403 });
    }
    if (!AUTH_SERVICE_URL) {
      throw new Error('AUTH_SERVICE_URL is not defined');
    }

    const body = await req.text();
    const response = await fetch(new URL('/api/auth/users', AUTH_SERVICE_URL).toString(), {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body,
      cache: 'no-store',
    });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('Unknown error', { status: 500 });
  }
}
