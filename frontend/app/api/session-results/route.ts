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
    const roomName = url.searchParams.get('roomName');
    const sessionId = url.searchParams.get('sessionId');

    if (!roomName && !sessionId) {
      return new NextResponse('roomName or sessionId is required', { status: 400 });
    }

    const judgeUrl = new URL('/api/session-results', JUDGE_SERVICE_URL);
    if (roomName) {
      judgeUrl.searchParams.set('room_name', roomName);
    }
    if (sessionId) {
      judgeUrl.searchParams.set('session_id', sessionId);
    }

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
