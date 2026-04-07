import { NextResponse } from 'next/server';
import { getAuthToken, getCurrentUser } from '@/lib/auth';

const BACKEND_SERVICE_URL = process.env.BACKEND_SERVICE_URL;

export const revalidate = 0;

export async function GET(req: Request) {
  try {
    const currentUser = await getCurrentUser();
    const token = await getAuthToken();
    if (!currentUser || !token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    if (!BACKEND_SERVICE_URL) {
      throw new Error('BACKEND_SERVICE_URL is not defined');
    }

    const url = new URL(req.url);
    const limit = url.searchParams.get('limit') ?? '50';

    const backendUrl = new URL('/api/sessions', BACKEND_SERVICE_URL);
    backendUrl.searchParams.set('limit', limit);

    const response = await fetch(backendUrl.toString(), {
      cache: 'no-store',
      headers: {
        Authorization: `Bearer ${token}`,
      },
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
