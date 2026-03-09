'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';

type ManagedUser = {
  user_id: string;
  email: string;
  role: 'manager' | 'coach';
};

export function CoachTrainingUsersView() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/users', {
        method: 'GET',
        cache: 'no-store',
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to load users');
      }
      const result = (await response.json()) as ManagedUser[];
      // Show only managers as trainees on the trainings page
      setUsers(result.filter((user) => user.role === 'manager'));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  return (
    <section className="bg-background min-h-svh w-full overflow-y-auto px-4 py-8 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Тренировки</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Выберите пользователя, чтобы посмотреть его тренировки.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link href="/">Новая тренировка</Link>
          </Button>
        </div>

        {loading && (
          <div className="border-border bg-card rounded-xl border p-6">
            <p className="text-sm">Загружаем список пользователей...</p>
          </div>
        )}

        {!loading && error && (
          <div className="border-border bg-card rounded-xl border p-6">
            <p className="text-sm text-red-600">{error}</p>
            <Button className="mt-4" variant="outline" onClick={() => void loadUsers()}>
              Повторить
            </Button>
          </div>
        )}

        {!loading && !error && (
          <div className="border-border bg-card rounded-xl border p-6">
            {users.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                Пользователи-менеджеры пока не созданы. Создайте их на странице пользователей.
              </p>
            ) : (
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[420px] text-left text-sm">
                  <thead className="text-muted-foreground">
                    <tr className="border-b">
                      <th className="px-3 py-2 font-medium">Email</th>
                      <th className="px-3 py-2 font-medium">ID</th>
                      <th className="px-3 py-2 font-medium">Тренировки</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.user_id} className="border-b last:border-b-0">
                        <td className="px-3 py-3">{user.email}</td>
                        <td className="text-muted-foreground px-3 py-3">
                          <code>{user.user_id}</code>
                        </td>
                        <td className="px-3 py-3">
                          <Link
                            href={`/sessions/user/${encodeURIComponent(user.user_id)}`}
                            className="text-primary hover:underline"
                          >
                            Открыть тренировки
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

