import { SessionResultView } from '@/components/app/session-result-view';
import { requireCurrentUser } from '@/lib/auth';

interface SessionDetailPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function SessionDetailPage({ params }: SessionDetailPageProps) {
  await requireCurrentUser();
  const { sessionId } = await params;

  return (
    <SessionResultView
      sessionId={decodeURIComponent(sessionId)}
      backHref="/sessions"
      backLabel="Все тренировки"
    />
  );
}
