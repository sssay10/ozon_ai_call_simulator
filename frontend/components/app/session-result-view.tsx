'use client';

import { useRouter } from 'next/navigation';
import { type ComponentProps, useCallback, useEffect, useState } from 'react';
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation';
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message';
import { Button } from '@/components/ui/button';

type TranscriptTurn = {
  role: string;
  text: string;
  created_at?: string | null;
};

type JudgeResult = {
  scenario_id: string;
  scores: Record<string, boolean | number | null>;
  total_score: number;
  critical_errors: string[];
  feedback_positive: string[];
  feedback_improvement: string[];
  recommendations: string[];
  client_profile: Record<string, unknown>;
  relevant_criteria: string[];
  model_used: string;
  judge_backend: string;
  error?: string | null;
  details?: string | null;
  created_at?: string | null;
};

type SessionResult = {
  session: {
    session_id: string;
    room_name: string;
    archetype: string;
    difficulty: string;
    product: string;
    started_at?: string | null;
    ended_at?: string | null;
  };
  transcript: TranscriptTurn[];
  judge_result: JudgeResult | null;
};

interface SessionResultViewProps {
  roomName?: string;
  sessionId?: string;
  onStartAnother?: () => void;
  backHref?: string;
  backLabel?: string;
}

function roleToMessageFrom(role: string): 'user' | 'assistant' {
  return role === 'manager' ? 'user' : 'assistant';
}

function roleToLabel(role: string): string {
  return role === 'manager' ? 'Менеджер' : 'Клиент';
}

function FeedbackSection({
  title,
  items,
  emptyLabel = 'Нет',
  itemClassName,
}: {
  title: string;
  items: string[];
  emptyLabel?: string;
  itemClassName: string;
}) {
  return (
    <div>
      <h3 className="font-medium">{title}</h3>
      <div className="mt-3 flex flex-col gap-3">
        {items.length === 0 ? (
          <div className="text-muted-foreground rounded-xl border border-dashed px-4 py-3 text-sm">
            {emptyLabel}
          </div>
        ) : (
          items.map((item, idx) => (
            <div key={idx} className={`rounded-xl border px-4 py-3 text-sm ${itemClassName}`}>
              {item}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function SessionResultView({
  roomName,
  sessionId,
  onStartAnother,
  backHref,
  backLabel = 'Назад',
}: ComponentProps<'section'> & SessionResultViewProps) {
  const router = useRouter();
  const [data, setData] = useState<SessionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const locale = typeof navigator !== 'undefined' ? navigator.language : 'en-US';

  const loadResults = useCallback(async () => {
    try {
      if (!sessionId && !roomName) {
        throw new Error('sessionId or roomName is required');
      }

      const url = new URL('/api/session-results', window.location.origin);
      if (sessionId) {
        url.searchParams.set('sessionId', sessionId);
      } else if (roomName) {
        url.searchParams.set('roomName', roomName);
      }

      const res = await fetch(url.toString(), {
        method: 'GET',
        cache: 'no-store',
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
      }

      const result = (await res.json()) as SessionResult;
      setData(result);
      setError(null);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load session results';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [roomName, sessionId]);

  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      const result = await loadResults();
      if (cancelled) {
        return;
      }
      if (!result?.judge_result) {
        timeoutId = setTimeout(poll, 2000);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [loadResults]);

  const handleRetry = () => {
    setLoading(true);
    void loadResults();
  };

  return (
    <section className="bg-background min-h-svh w-full overflow-y-auto px-4 py-8 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-foreground text-2xl font-semibold">Результат тренировки</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Комната: <code>{data?.session.room_name ?? roomName ?? sessionId}</code>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {backHref && (
              <Button variant="outline" onClick={() => router.push(backHref)}>
                {backLabel}
              </Button>
            )}
            {onStartAnother && (
              <Button variant="outline" onClick={onStartAnother}>
                Новый звонок
              </Button>
            )}
          </div>
        </div>

        {loading && (
          <div className="border-border bg-card rounded-xl border p-6">
            <p className="text-sm">Загружаем транскрипт и результаты оценки...</p>
          </div>
        )}

        {!loading && error && (
          <div className="border-border bg-card rounded-xl border p-6">
            <p className="text-sm text-red-600">{error}</p>
            <Button className="mt-4" variant="outline" onClick={handleRetry}>
              Повторить
            </Button>
          </div>
        )}

        {!loading && data && (
          <>
            <div className="grid gap-4 md:grid-cols-4">
              <div className="border-border bg-card rounded-xl border p-4">
                <div className="text-muted-foreground text-xs uppercase">Архетип</div>
                <div className="mt-2 text-sm font-medium">{data.session.archetype}</div>
              </div>
              <div className="border-border bg-card rounded-xl border p-4">
                <div className="text-muted-foreground text-xs uppercase">Сложность</div>
                <div className="mt-2 text-sm font-medium">{data.session.difficulty}</div>
              </div>
              <div className="border-border bg-card rounded-xl border p-4">
                <div className="text-muted-foreground text-xs uppercase">Тема</div>
                <div className="mt-2 text-sm font-medium">{data.session.product}</div>
              </div>
              <div className="border-border bg-card rounded-xl border p-4">
                <div className="text-muted-foreground text-xs uppercase">Итоговый балл</div>
                <div className="mt-2 text-2xl font-semibold">
                  {data.judge_result ? data.judge_result.total_score : '...'}
                </div>
              </div>
            </div>

            <div className="border-border bg-card rounded-xl border p-6">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Транскрипт диалога</h2>
                  {data.session.started_at && (
                    <p className="text-muted-foreground mt-1 text-xs">
                      {new Date(data.session.started_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
              <div className="mt-4 h-[420px] overflow-hidden rounded-xl border">
                <Conversation className="h-full">
                  <ConversationContent className="mx-auto w-full max-w-2xl gap-4 px-4 py-5 md:px-6">
                    {data.transcript.length === 0 && (
                      <p className="text-muted-foreground text-sm">Транскрипт пока пуст.</p>
                    )}
                    {data.transcript.map((turn, idx) => {
                      const messageFrom = roleToMessageFrom(turn.role);
                      const createdAt = turn.created_at ? new Date(turn.created_at) : null;
                      const timeLabel =
                        createdAt?.toLocaleTimeString(locale, {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        }) ?? null;
                      const timeTitle =
                        createdAt?.toLocaleString(locale, {
                          dateStyle: 'medium',
                          timeStyle: 'medium',
                        }) ?? null;

                      return (
                        <Message key={`${turn.role}-${idx}`} from={messageFrom}>
                          <div
                            className={`text-muted-foreground mb-1 text-[11px] uppercase ${
                              messageFrom === 'user' ? 'self-end text-right' : 'self-start'
                            }`}
                            title={timeTitle ?? undefined}
                          >
                            {roleToLabel(turn.role)}
                            {timeLabel && (
                              <span className="text-muted-foreground/80 ml-2 normal-case">
                                {timeLabel}
                              </span>
                            )}
                          </div>
                          <MessageContent
                            className={
                              messageFrom === 'assistant'
                                ? 'rounded-lg border px-4 py-3'
                                : 'rounded-[22px]'
                            }
                          >
                            <MessageResponse className="whitespace-pre-wrap">
                              {turn.text}
                            </MessageResponse>
                          </MessageContent>
                        </Message>
                      );
                    })}
                  </ConversationContent>
                  <ConversationScrollButton />
                </Conversation>
              </div>
            </div>

            <div className="border-border bg-card rounded-xl border p-6">
              <h2 className="text-lg font-semibold">Результат оценки</h2>

              {!data.judge_result && (
                <p className="text-muted-foreground mt-4 text-sm">
                  Оценка еще выполняется. Страница обновится автоматически.
                </p>
              )}

              {data.judge_result && (
                <div className="mt-4 flex flex-col gap-6">
                  <div>
                    <div className="text-muted-foreground text-xs uppercase">Сценарий</div>
                    <div className="mt-1 text-sm">{data.judge_result.scenario_id}</div>
                  </div>

                  <div>
                    <h3 className="font-medium">Оценки по параметрам</h3>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      {Object.entries(data.judge_result.scores).map(([key, value]) => (
                        <div key={key} className="rounded-lg border p-3 text-sm">
                          <div className="text-muted-foreground text-xs">{key}</div>
                          <div className="mt-1 font-medium">{String(value)}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <FeedbackSection
                    title="Что хорошо"
                    items={data.judge_result.feedback_positive}
                    itemClassName="border-green-500/20 bg-green-500/10 text-green-950 dark:text-green-100"
                  />

                  <FeedbackSection
                    title="Что улучшить"
                    items={data.judge_result.feedback_improvement}
                    itemClassName="border-yellow-500/20 bg-yellow-500/10 text-yellow-950 dark:text-yellow-100"
                  />

                  <FeedbackSection
                    title="Рекомендации"
                    items={data.judge_result.recommendations}
                    itemClassName="border-amber-500/20 bg-amber-500/10 text-amber-950 dark:text-amber-100"
                  />

                  <FeedbackSection
                    title="Критические ошибки"
                    items={data.judge_result.critical_errors}
                    itemClassName="border-red-500/20 bg-red-500/10 text-red-950 dark:text-red-100"
                  />
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
