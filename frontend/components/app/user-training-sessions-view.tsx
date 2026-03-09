'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { TrainingSessionsView } from '@/components/app/training-sessions-view';

type TrainingSessionsByUserViewProps = {
  userId: string;
  userEmail?: string;
};

export function UserTrainingSessionsView({ userId, userEmail }: TrainingSessionsByUserViewProps) {
  const title = useMemo(
    () => (userEmail ? `Тренировки пользователя ${userEmail}` : 'Тренировки выбранного пользователя'),
    [userEmail],
  );

  return (
    <div className="bg-background min-h-svh w-full overflow-y-auto px-4 py-8 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">{title}</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Отображаются тренировки только выбранного пользователя.
            </p>
          </div>
          <div className="flex gap-3">
            <Button asChild variant="outline">
              <Link href="/sessions">Все пользователи</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/">Новая тренировка</Link>
            </Button>
          </div>
        </div>

        <TrainingSessionsView ownerUserId={userId} hideHeader />
      </div>
    </div>
  );
}

