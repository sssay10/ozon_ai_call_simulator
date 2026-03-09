import { redirect } from 'next/navigation';
import { UsersManagementView } from '@/components/app/users-management-view';
import { requireCurrentUser } from '@/lib/auth';

export default async function UsersPage() {
  const currentUser = await requireCurrentUser();
  if (currentUser.role !== 'coach') {
    redirect('/');
  }

  return <UsersManagementView />;
}
