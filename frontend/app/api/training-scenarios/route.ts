import { NextResponse } from 'next/server';
import { getCurrentUser, getRoleAccessHeaders } from '@/lib/auth';

const JUDGE_SERVICE_URL = process.env.JUDGE_SERVICE_URL;

export const revalidate = 0;

function assertJudgeServiceUrl() {
  if (!JUDGE_SERVICE_URL) {
    throw new Error('JUDGE_SERVICE_URL is not defined');
  }
  return JUDGE_SERVICE_URL;
}

export async function GET() {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const judgeUrl = new URL('/api/training-scenarios', assertJudgeServiceUrl());
    const response = await fetch(judgeUrl.toString(), {
      method: 'GET',
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
    return new NextResponse(error instanceof Error ? error.message : 'Unknown error', { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const judgeUrl = new URL('/api/training-scenarios', assertJudgeServiceUrl());
    const response = await fetch(judgeUrl.toString(), {
      method: 'POST',
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
