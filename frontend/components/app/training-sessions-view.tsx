'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';

type TrainingSessionSummary = {
  session_id: string;
  owner_user_id: string;
  room_name: string;
  product: string;
  started_at?: string | null;
  ended_at?: string | null;
  total_score?: number | null;
  judge_ready: boolean;
  scenario_id?: string | null;
};

type TrainingSessionsViewProps = {
  ownerUserId?: string;
  hideHeader?: boolean;
};

function SessionsScoreChart({ sessions }: { sessions: TrainingSessionSummary[] }) {
  const chartSessions = useMemo(() => {
    return [...sessions]
      .filter((session) => typeof session.total_score === 'number')
      .sort((a, b) => {
        const aTime = a.started_at ? new Date(a.started_at).getTime() : 0;
        const bTime = b.started_at ? new Date(b.started_at).getTime() : 0;
        return aTime - bTime;
      })
      .map((session, index) => ({
        ...session,
        order: index + 1,
        total_score: Number(session.total_score ?? 0),
      }));
  }, [sessions]);

  if (chartSessions.length === 0) {
    return (
      <div className="border-border bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold">Динамика итогового балла</h2>
        <p className="text-muted-foreground mt-3 text-sm">
          График появится, когда будет хотя бы одна оцененная тренировка.
        </p>
      </div>
    );
  }

  const width = 760;
  const height = 280;
  const marginTop = 24;
  const marginRight = 20;
  const marginBottom = 48;
  const marginLeft = 40;
  const plotWidth = width - marginLeft - marginRight;
  const plotHeight = height - marginTop - marginBottom;

  const points = chartSessions.map((session, index) => {
    const x =
      chartSessions.length === 1
        ? marginLeft + plotWidth / 2
        : marginLeft + (index / (chartSessions.length - 1)) * plotWidth;
    const y = marginTop + ((10 - session.total_score) / 10) * plotHeight;
    return { ...session, x, y };
  });

  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
  const areaPath = `${linePath} L ${points.at(-1)?.x ?? marginLeft} ${marginTop + plotHeight} L ${points[0]?.x ?? marginLeft} ${marginTop + plotHeight} Z`;
  const yTicks = [0, 2, 4, 6, 8, 10];
  const xLabelStep = chartSessions.length > 8 ? Math.ceil(chartSessions.length / 6) : 1;

  return (
    <div className="border-border bg-card rounded-xl border p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Динамика итогового балла</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            По оси X: номер и дата тренировки. По оси Y: итоговый балл.
          </p>
        </div>
        <div className="text-right">
          <div className="text-muted-foreground text-xs uppercase">Последний балл</div>
          <div className="mt-1 text-2xl font-semibold">
            {chartSessions.at(-1)?.total_score.toFixed(1)}
          </div>
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-[280px] w-full min-w-[680px]"
          role="img"
          aria-label="График итоговых баллов по тренировкам"
        >
          <defs>
            <linearGradient id="score-area-gradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.22" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {yTicks.map((tick) => {
            const y = marginTop + ((10 - tick) / 10) * plotHeight;
            return (
              <g key={tick}>
                <line
                  x1={marginLeft}
                  y1={y}
                  x2={width - marginRight}
                  y2={y}
                  className="stroke-border"
                  strokeDasharray="4 6"
                />
                <text x={marginLeft - 10} y={y + 4} textAnchor="end" className="fill-muted-foreground text-[11px]">
                  {tick}
                </text>
              </g>
            );
          })}

          <path d={areaPath} fill="url(#score-area-gradient)" className="text-primary" />
          <path
            d={linePath}
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-primary"
          />

          {points.map((point, index) => (
            <g key={point.session_id}>
              <circle cx={point.x} cy={point.y} r="5" className="fill-primary stroke-background" strokeWidth="3" />
              <text x={point.x} y={point.y - 12} textAnchor="middle" className="fill-foreground text-[11px] font-medium">
                {point.total_score.toFixed(1)}
              </text>
              {(index % xLabelStep === 0 || index === points.length - 1) && (
                <>
                  <text
                    x={point.x}
                    y={height - 22}
                    textAnchor="middle"
                    className="fill-muted-foreground text-[11px]"
                  >
                    {point.order}
                  </text>
                  <text
                    x={point.x}
                    y={height - 8}
                    textAnchor="middle"
                    className="fill-muted-foreground text-[10px]"
                  >
                    {point.started_at ? new Date(point.started_at).toLocaleDateString() : ''}
                  </text>
                </>
              )}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

export function TrainingSessionsView({ ownerUserId, hideHeader = false }: TrainingSessionsViewProps = {}) {
  const [sessions, setSessions] = useState<TrainingSessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      const url = new URL('/api/training-sessions', window.location.origin);
      url.searchParams.set('limit', '100');

      const res = await fetch(url.toString(), {
        method: 'GET',
        cache: 'no-store',
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
      }

      const result = (await res.json()) as TrainingSessionSummary[];
      setSessions(result);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load sessions';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const filteredSessions = useMemo(
    () => (ownerUserId ? sessions.filter((session) => session.owner_user_id === ownerUserId) : sessions),
    [sessions, ownerUserId],
  );

  return (
    <section className="bg-background min-h-svh w-full overflow-y-auto px-4 py-8 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        {!hideHeader && (
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-foreground text-2xl font-semibold">Все тренировки</h1>
              <p className="text-muted-foreground mt-1 text-sm">
                История завершенных и оцениваемых сессий.
              </p>
            </div>
            <Button asChild variant="outline">
              <Link href="/">Новая тренировка</Link>
            </Button>
          </div>
        )}

        {loading && (
          <div className="border-border bg-card rounded-xl border p-6">
            <p className="text-sm">Загружаем список тренировок...</p>
          </div>
        )}

        {!loading && error && (
          <div className="border-border bg-card rounded-xl border p-6">
            <p className="text-sm text-red-600">{error}</p>
            <Button className="mt-4" variant="outline" onClick={() => void loadSessions()}>
              Повторить
            </Button>
          </div>
        )}

        {!loading && !error && (
          <div className="grid gap-4">
            <SessionsScoreChart sessions={filteredSessions} />

            {filteredSessions.length === 0 && (
              <div className="border-border bg-card rounded-xl border p-6">
                <p className="text-muted-foreground text-sm">Сохраненных тренировок пока нет.</p>
              </div>
            )}

            {filteredSessions.map((session) => (
              <Link
                key={session.session_id}
                href={`/sessions/${session.session_id}`}
                className="border-border bg-card hover:bg-accent/20 rounded-xl border p-5 transition"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <div className="truncate text-base font-semibold">{session.product}</div>
                    {session.scenario_id && (
                      <div className="text-muted-foreground mt-1 text-xs">
                        Рубрика оценки: <code>{session.scenario_id}</code>
                      </div>
                    )}
                    <div className="text-muted-foreground mt-3 text-xs">
                      Комната: <code>{session.room_name}</code>
                    </div>
                    <div className="text-muted-foreground mt-1 text-xs">
                      {session.started_at
                        ? new Date(session.started_at).toLocaleString()
                        : 'Без даты'}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-col items-start gap-2 md:items-end">
                    <div className="text-right">
                      <div className="text-muted-foreground text-xs uppercase">Итоговый балл</div>
                      <div className="mt-1 text-2xl font-semibold">
                        {session.total_score ?? '...'}
                      </div>
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {session.judge_ready ? 'Оценка готова' : 'Оценка выполняется'}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
