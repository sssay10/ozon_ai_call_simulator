import { NextResponse } from 'next/server';
import { getAuthToken, getCurrentUser } from '@/lib/auth';

const BACKEND_SERVICE_URL = process.env.BACKEND_SERVICE_URL;

export const revalidate = 0;

function assertBackendServiceUrl() {
  if (!BACKEND_SERVICE_URL) {
    throw new Error('BACKEND_SERVICE_URL is not defined');
  }
  return BACKEND_SERVICE_URL;
}

export async function GET() {
  try {
    const currentUser = await getCurrentUser();
    const token = await getAuthToken();
    if (!currentUser || !token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const backendUrl = new URL('/api/training-scenarios', assertBackendServiceUrl());
    const response = await fetch(backendUrl.toString(), {
      method: 'GET',
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
    return new NextResponse(error instanceof Error ? error.message : 'Unknown error', { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const currentUser = await getCurrentUser();
    const token = await getAuthToken();
    if (!currentUser || !token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const backendUrl = new URL('/api/training-scenarios', assertBackendServiceUrl());
    const response = await fetch(backendUrl.toString(), {
      method: 'POST',
      cache: 'no-store',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: await req.text(),
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
    return new NextResponse(error instanceof Error ? error.message : 'Unknown error', { status: 500 });
  }
}
