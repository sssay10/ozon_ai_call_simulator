import { NextResponse } from 'next/server';
import { getCurrentUser, getRoleAccessHeaders } from '@/lib/auth';

const JUDGE_SERVICE_URL = process.env.JUDGE_SERVICE_URL;

export const revalidate = 0;

export async function GET(req: Request) {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    if (!JUDGE_SERVICE_URL) {
      throw new Error('JUDGE_SERVICE_URL is not defined');
    }

    const url = new URL(req.url);
    const limit = url.searchParams.get('limit') ?? '50';

    const judgeUrl = new URL('/api/sessions', JUDGE_SERVICE_URL);
    judgeUrl.searchParams.set('limit', limit);

    const response = await fetch(judgeUrl.toString(), {
      cache: 'no-store',
      headers: getRoleAccessHeaders(currentUser),
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
