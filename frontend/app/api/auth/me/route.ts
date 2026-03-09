import { NextResponse } from 'next/server';
import { getCurrentUser } from '@/lib/auth';

export const revalidate = 0;

export async function GET() {
  const user = await getCurrentUser();
  if (!user) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  return NextResponse.json(user, {
    headers: { 'Cache-Control': 'no-store' },
  });
}
