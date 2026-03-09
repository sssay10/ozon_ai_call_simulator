import { TrainingSessionsView } from '@/components/app/training-sessions-view';
import { CoachTrainingUsersView } from '@/components/app/coach-training-users-view';
import { requireCurrentUser } from '@/lib/auth';

export default async function SessionsPage() {
  const currentUser = await requireCurrentUser();
  if (currentUser.role === 'coach') {
    return <CoachTrainingUsersView />;
  }

  return <TrainingSessionsView />;
}
