import { redirect } from 'next/navigation';
import { LoginForm } from '@/components/app/login-form';
import { getCurrentUser } from '@/lib/auth';

export default async function LoginPage() {
  const user = await getCurrentUser();
  if (user) {
    redirect('/');
  }

  return (
    <main className="bg-background flex min-h-svh items-center justify-center px-4 py-8">
      <LoginForm />
    </main>
  );
}
