import { redirect } from 'next/navigation';
import { requireCurrentUser } from '@/lib/auth';
import { UserTrainingSessionsView } from '@/components/app/user-training-sessions-view';

interface UserSessionsPageProps {
  params: Promise<{
    userId: string;
  }>;
}

export default async function UserSessionsPage({ params }: UserSessionsPageProps) {
  const currentUser = await requireCurrentUser();
  if (currentUser.role !== 'coach') {
    redirect('/sessions');
  }

  const { userId } = await params;

  return <UserTrainingSessionsView userId={decodeURIComponent(userId)} />;
}

