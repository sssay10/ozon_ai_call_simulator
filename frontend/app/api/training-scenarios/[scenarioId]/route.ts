import { NextResponse } from 'next/server';
import { getAuthToken, getCurrentUser } from '@/lib/auth';

const BACKEND_SERVICE_URL = process.env.BACKEND_SERVICE_URL;

export const revalidate = 0;

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ scenarioId: string }> }
) {
  try {
    const currentUser = await getCurrentUser();
    const token = await getAuthToken();
    if (!currentUser || !token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }
    if (!BACKEND_SERVICE_URL) {
      throw new Error('BACKEND_SERVICE_URL is not defined');
    }

    const { scenarioId } = await params;
    const backendUrl = new URL(
      `/api/training-scenarios/${encodeURIComponent(scenarioId)}`,
      BACKEND_SERVICE_URL
    );
    const response = await fetch(backendUrl.toString(), {
      method: 'PUT',
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
