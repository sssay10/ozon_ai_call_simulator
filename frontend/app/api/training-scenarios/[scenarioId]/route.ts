import { NextResponse } from 'next/server';
import { getCurrentUser, getRoleAccessHeaders } from '@/lib/auth';

const JUDGE_SERVICE_URL = process.env.JUDGE_SERVICE_URL;

export const revalidate = 0;

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ scenarioId: string }> }
) {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser) {
      return new NextResponse('Unauthorized', { status: 401 });
    }
    if (!JUDGE_SERVICE_URL) {
      throw new Error('JUDGE_SERVICE_URL is not defined');
    }

    const { scenarioId } = await params;
    const judgeUrl = new URL(
      `/api/training-scenarios/${encodeURIComponent(scenarioId)}`,
      JUDGE_SERVICE_URL
    );
    const response = await fetch(judgeUrl.toString(), {
      method: 'PUT',
      cache: 'no-store',
      headers: {
        ...getRoleAccessHeaders(currentUser),
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
