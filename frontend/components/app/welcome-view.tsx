'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { MutableRefObject } from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DEFAULT_SESSION_SETTINGS } from '@/lib/session-settings';
import type { SessionSettings } from '@/lib/session-settings';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-fg0 mb-4 size-16"
    >
      <path
        d="M15 24V40C15 40.7957 14.6839 41.5587 14.1213 42.1213C13.5587 42.6839 12.7956 43 12 43C11.2044 43 10.4413 42.6839 9.87868 42.1213C9.31607 41.5587 9 40.7957 9 40V24C9 23.2044 9.31607 22.4413 9.87868 21.8787C10.4413 21.3161 11.2044 21 12 21C12.7956 21 13.5587 21.3161 14.1213 21.8787C14.6839 22.4413 15 23.2044 15 24ZM22 5C21.2044 5 20.4413 5.31607 19.8787 5.87868C19.3161 6.44129 19 7.20435 19 8V56C19 56.7957 19.3161 57.5587 19.8787 58.1213C20.4413 58.6839 21.2044 59 22 59C22.7956 59 23.5587 58.6839 24.1213 58.1213C24.6839 57.5587 25 56.7957 25 56V8C25 7.20435 24.6839 6.44129 24.1213 5.87868C23.5587 5.31607 22.7956 5 22 5ZM32 13C31.2044 13 30.4413 13.3161 29.8787 13.8787C29.3161 14.4413 29 15.2044 29 16V48C29 48.7957 29.3161 49.5587 29.8787 50.1213C30.4413 50.6839 31.2044 51 32 51C32.7956 51 33.5587 50.6839 34.1213 50.1213C34.6839 49.5587 35 48.7957 35 48V16C35 15.2044 34.6839 14.4413 34.1213 13.8787C33.5587 13.3161 32.7956 13 32 13ZM42 21C41.2043 21 40.4413 21.3161 39.8787 21.8787C39.3161 22.4413 39 23.2044 39 24V40C39 40.7957 39.3161 41.5587 39.8787 42.1213C40.4413 42.6839 41.2043 43 42 43C42.7957 43 43.5587 42.6839 44.1213 42.1213C44.6839 41.5587 45 40.7957 45 40V24C45 23.2044 44.6839 22.4413 44.1213 21.8787C43.5587 21.3161 42.7957 21 42 21ZM52 17C51.2043 17 50.4413 17.3161 49.8787 17.8787C49.3161 18.4413 49 19.2044 49 20V44C49 44.7957 49.3161 45.5587 49.8787 46.1213C50.4413 46.6839 51.2043 47 52 47C52.7957 47 53.5587 46.6839 54.1213 46.1213C54.6839 45.5587 55 44.7957 55 44V20C55 19.2044 54.6839 18.4413 54.1213 17.8787C53.5587 17.3161 52.7957 17 52 17Z"
        fill="currentColor"
      />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  sessionSettingsRef: MutableRefObject<SessionSettings>;
  currentUserRole: 'manager' | 'coach';
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  sessionSettingsRef,
  currentUserRole,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  type TrainingScenario = {
    id: string;
    name: string;
    persona_description: string;
    main_pain: string;
  };
  const emptyForm = {
    name: '',
    persona_description: '',
    main_pain: '',
  };

  const [settings, setSettings] = useState<SessionSettings>(DEFAULT_SESSION_SETTINGS);
  const [scenarios, setScenarios] = useState<TrainingScenario[]>([]);
  const [loadingScenarios, setLoadingScenarios] = useState(true);
  const [scenariosError, setScenariosError] = useState<string | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [editingScenarioId, setEditingScenarioId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    sessionSettingsRef.current = settings;
  }, [settings, sessionSettingsRef]);

  const loadScenarios = async () => {
    try {
      setLoadingScenarios(true);
      const response = await fetch('/api/training-scenarios', {
        method: 'GET',
        cache: 'no-store',
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to load training scenarios');
      }
      const data = (await response.json()) as TrainingScenario[];
      setScenarios(data);
      setScenariosError(null);
      if (currentUserRole === 'manager' && data.length > 0 && !selectedScenarioId) {
        setSelectedScenarioId(data[0].id);
      }
    } catch (error) {
      setScenariosError(error instanceof Error ? error.message : 'Failed to load training scenarios');
    } finally {
      setLoadingScenarios(false);
    }
  };

  useEffect(() => {
    void loadScenarios();
  }, []);

  useEffect(() => {
    if (currentUserRole !== 'manager') {
      return;
    }
    const selected = scenarios.find((item) => item.id === selectedScenarioId);
    if (!selected) {
      return;
    }
    setSettings({
      ...DEFAULT_SESSION_SETTINGS,
      product: selected.name,
      training_scenario_id: selected.id,
      training_scenario_name: selected.name,
      prompt_blocks: {
        persona_description: selected.persona_description,
        main_pain: selected.main_pain,
      },
    });
  }, [currentUserRole, scenarios, selectedScenarioId]);

  const beginCreateScenario = () => {
    setEditingScenarioId(null);
    setForm(emptyForm);
    setSaveError(null);
  };

  const beginEditScenario = (scenario: TrainingScenario) => {
    setEditingScenarioId(scenario.id);
    setForm({
      name: scenario.name,
      persona_description: scenario.persona_description,
      main_pain: scenario.main_pain,
    });
    setSaveError(null);
  };

  const saveScenario = async () => {
    if (!form.name.trim() || !form.persona_description.trim() || !form.main_pain.trim()) {
      setSaveError('Заполните все поля сценария.');
      return;
    }

    try {
      setSaving(true);
      const isEdit = Boolean(editingScenarioId);
      const response = await fetch(
        isEdit ? `/api/training-scenarios/${encodeURIComponent(editingScenarioId!)}` : '/api/training-scenarios',
        {
          method: isEdit ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form),
        }
      );
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to save training scenario');
      }
      setSaveError(null);
      beginCreateScenario();
      await loadScenarios();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Failed to save training scenario');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      ref={ref}
      className={
        currentUserRole === 'coach'
          ? 'flex min-h-0 w-full min-w-0 flex-1 flex-col'
          : undefined
      }
    >
      <section
        className={
          currentUserRole === 'coach'
            ? 'bg-background flex min-h-0 w-full flex-1 flex-col items-center justify-start px-4 pb-4 pt-4 text-center'
            : 'bg-background flex flex-col items-center justify-center text-center'
        }
      >
        <div className={currentUserRole === 'coach' ? 'shrink-0' : undefined}>
          <WelcomeImage />
        </div>

        <p
          className={
            currentUserRole === 'coach'
              ? 'text-foreground max-w-prose shrink-0 pt-1 leading-6 font-medium'
              : 'text-foreground max-w-prose pt-1 leading-6 font-medium'
          }
        >
          {currentUserRole === 'coach'
            ? 'Создавайте и редактируйте тренировочные сценарии для менеджеров'
            : 'Выберите тренировку и начните звонок'}
        </p>

        {loadingScenarios && <p className="text-muted-foreground mt-4 text-sm">Загрузка сценариев...</p>}

        {!loadingScenarios && scenariosError && <p className="mt-4 text-sm text-red-600">{scenariosError}</p>}

        {!loadingScenarios && !scenariosError && currentUserRole === 'manager' && (
          <div className="mt-4 w-full max-w-xl text-left">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground whitespace-nowrap text-sm">Тренировка:</span>
              <Select value={selectedScenarioId} onValueChange={setSelectedScenarioId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Выберите сценарий" />
                </SelectTrigger>
                <SelectContent>
                  {scenarios.map((scenario) => (
                    <SelectItem key={scenario.id} value={scenario.id}>
                      {scenario.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedScenarioId && (
              <div className="border-border bg-card mt-3 rounded-lg border p-3 text-xs">
                {(() => {
                  const selected = scenarios.find((item) => item.id === selectedScenarioId);
                  if (!selected) {
                    return null;
                  }
                  return (
                    <>
                      <div>
                        <strong>Персона (кто клиент):</strong> {selected.persona_description}
                      </div>
                      <div className="mt-2">
                        <strong>Основная боль клиента:</strong> {selected.main_pain}
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {!loadingScenarios && !scenariosError && currentUserRole === 'coach' && (
          <div className="mt-4 grid w-full max-w-5xl min-h-0 min-w-0 flex-1 gap-4 text-left md:grid-cols-2 md:items-stretch">
            <div className="border-border bg-card flex min-h-0 flex-col rounded-xl border p-4">
              <div className="mb-3 flex shrink-0 items-center justify-between">
                <h2 className="text-base font-semibold">Сценарии</h2>
                <Button type="button" size="sm" variant="outline" onClick={beginCreateScenario}>
                  Новый
                </Button>
              </div>
              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                {scenarios.map((scenario) => (
                  <button
                    key={scenario.id}
                    type="button"
                    className="border-border hover:bg-accent/30 w-full rounded-md border p-3 text-left text-sm"
                    onClick={() => beginEditScenario(scenario)}
                  >
                    <div className="font-medium">{scenario.name}</div>
                    <div className="text-muted-foreground mt-1 line-clamp-2 text-xs">
                      {scenario.persona_description}
                    </div>
                  </button>
                ))}
                {scenarios.length === 0 && (
                  <p className="text-muted-foreground text-sm">Сценариев пока нет. Создайте первый.</p>
                )}
              </div>
            </div>

            <div className="border-border bg-card flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border p-4">
              <h2 className="mb-3 shrink-0 text-base font-semibold">
                {editingScenarioId ? 'Редактирование сценария' : 'Создание сценария'}
              </h2>
              <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                <div className="space-y-3">
                  <label className="block text-left text-sm">
                    Название
                    <input
                      value={form.name}
                      onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                      className="border-border bg-background mt-1 w-full rounded-md border px-3 py-2"
                    />
                  </label>
                  <label className="block text-left text-sm">
                    Персона — кто клиент (характер, мотивация, тон)
                    <textarea
                      value={form.persona_description}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, persona_description: e.target.value }))
                      }
                      rows={5}
                      className="border-border bg-background mt-1 min-h-[120px] w-full resize-y rounded-md border px-3 py-2"
                    />
                  </label>
                  <label className="block text-left text-sm">
                    Основная боль клиента (раскрывать после квалификации)
                    <textarea
                      value={form.main_pain}
                      onChange={(e) => setForm((prev) => ({ ...prev, main_pain: e.target.value }))}
                      rows={4}
                      className="border-border bg-background mt-1 min-h-[100px] w-full resize-y rounded-md border px-3 py-2"
                    />
                  </label>
                  {saveError && <p className="text-left text-sm text-red-600">{saveError}</p>}
                </div>
              </div>
              <div className="border-border mt-4 flex shrink-0 gap-2 border-t pt-4">
                <Button type="button" onClick={saveScenario} disabled={saving}>
                  {saving ? 'Сохраняем...' : editingScenarioId ? 'Сохранить' : 'Создать'}
                </Button>
                {editingScenarioId && (
                  <Button type="button" variant="outline" onClick={beginCreateScenario} disabled={saving}>
                    Отмена
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        <div
          className={
            currentUserRole === 'coach'
              ? 'mt-6 flex shrink-0 flex-col items-center gap-3 sm:flex-row'
              : 'mt-6 flex flex-col items-center gap-3 sm:flex-row'
          }
        >
          {currentUserRole === 'manager' && (
            <Button
              size="lg"
              onClick={onStartCall}
              disabled={!selectedScenarioId}
              className="w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase"
            >
              {startButtonText}
            </Button>
          )}
          <Button asChild size="lg" variant="outline" className="w-64 rounded-full">
            <Link href="/sessions">История тренировок</Link>
          </Button>
        </div>
      </section>

    </div>
  );
};
