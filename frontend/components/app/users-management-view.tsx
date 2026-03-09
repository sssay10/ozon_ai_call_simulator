'use client';

import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';

type ManagedUser = {
  user_id: string;
  email: string;
  role: 'manager' | 'coach';
};

export function UsersManagementView() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'manager' | 'coach'>('manager');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
      setUsers(result);
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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/auth/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, role }),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to create user');
      }

      const createdUser = (await response.json()) as ManagedUser;
      setUsers((current) => [...current, createdUser]);
      setEmail('');
      setPassword('');
      setRole('manager');
      setSuccess(`Пользователь ${createdUser.email} создан`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-background min-h-svh w-full overflow-y-auto px-4 py-8 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div>
          <h1 className="text-foreground text-2xl font-semibold">Пользователи</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Только коуч может создавать новых пользователей.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="border-border bg-card rounded-xl border p-6">
          <h2 className="text-lg font-semibold">Создать пользователя</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-2 text-sm">
              <span className="text-muted-foreground">Email</span>
              <input
                className="border-input bg-background rounded-md border px-3 py-2 outline-none"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label className="flex flex-col gap-2 text-sm">
              <span className="text-muted-foreground">Пароль</span>
              <input
                className="border-input bg-background rounded-md border px-3 py-2 outline-none"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
              />
            </label>
            <label className="flex flex-col gap-2 text-sm">
              <span className="text-muted-foreground">Роль</span>
              <select
                className="border-input bg-background rounded-md border px-3 py-2 outline-none"
                value={role}
                onChange={(event) => setRole(event.target.value as 'manager' | 'coach')}
              >
                <option value="manager">manager</option>
                <option value="coach">coach</option>
              </select>
            </label>
          </div>

          {error && (
            <div className="mt-4 rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-200">
              {error}
            </div>
          )}
          {success && (
            <div className="mt-4 rounded-md border border-green-500/20 bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-200">
              {success}
            </div>
          )}

          <Button className="mt-4" type="submit" disabled={submitting}>
            {submitting ? 'Создаем...' : 'Создать пользователя'}
          </Button>
        </form>

        <div className="border-border bg-card rounded-xl border p-6">
          <h2 className="text-lg font-semibold">Список пользователей</h2>
          {loading ? (
            <p className="text-muted-foreground mt-4 text-sm">Загружаем пользователей...</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[420px] text-left text-sm">
                <thead className="text-muted-foreground">
                  <tr className="border-b">
                    <th className="px-3 py-2 font-medium">Email</th>
                    <th className="px-3 py-2 font-medium">Роль</th>
                    <th className="px-3 py-2 font-medium">ID</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.user_id} className="border-b last:border-b-0">
                      <td className="px-3 py-3">{user.email}</td>
                      <td className="px-3 py-3 uppercase">{user.role}</td>
                      <td className="text-muted-foreground px-3 py-3">
                        <code>{user.user_id}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
