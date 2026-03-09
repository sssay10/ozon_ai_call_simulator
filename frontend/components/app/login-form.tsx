'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('manager@example.com');
  const [password, setPassword] = useState('manager123');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Login failed');
      }

      router.push('/');
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-border bg-card w-full max-w-md rounded-2xl border p-6 shadow-sm">
      <div>
        <h1 className="text-2xl font-semibold">
          {mode === 'login' ? 'Вход' : 'Регистрация менеджера'}
        </h1>
        <p className="text-muted-foreground mt-2 text-sm">
          {mode === 'login'
            ? 'Войдите как менеджер или коуч, чтобы начать тренировки и смотреть статистику.'
            : 'Создайте аккаунт менеджера, чтобы проходить тренировки и смотреть свои результаты.'}
        </p>
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-muted-foreground">Email</span>
          <input
            className="border-input bg-background rounded-md border px-3 py-2 outline-none"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
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
            autoComplete="current-password"
            required
          />
        </label>
      </div>

      {error && <div className="mt-4 rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-200">{error}</div>}

      <Button className="mt-6 w-full" type="submit" disabled={isSubmitting}>
        {isSubmitting ? (mode === 'login' ? 'Входим...' : 'Создаем...') : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
      </Button>

      <div className="text-muted-foreground mt-4 flex flex-col gap-1 text-xs">
        {mode === 'login' ? (
          <>
            <p>
              Нет аккаунта?{' '}
              <button
                type="button"
                className="text-primary underline underline-offset-2"
                onClick={() => {
                  setMode('register');
                  setError(null);
                }}
              >
                Создать аккаунт менеджера
              </button>
            </p>
            <p className="mt-1">Тестовые пользователи: `manager@example.com` / `manager123`, `coach@example.com` / `coach123`</p>
          </>
        ) : (
          <p>
            Уже есть аккаунт?{' '}
            <button
              type="button"
              className="text-primary underline underline-offset-2"
              onClick={() => {
                setMode('login');
                setError(null);
              }}
            >
              Войти
            </button>
          </p>
        )}
      </div>
    </form>
  );
}
