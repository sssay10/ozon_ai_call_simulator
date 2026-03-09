/**
 * Session settings for the voice agent (archetype, difficulty, product).
 * Must match agent-starter-python session_settings.py.
 */
export interface SessionSettings {
  archetype: keyof typeof ARCHETYPES;
  difficulty: keyof typeof DIFFICULTY;
  product: keyof typeof PRODUCTS;
}

export const ARCHETYPES = {
  novice: { name: 'Новичок' },
  skeptic: { name: 'Скептик' },
  busy_owner: { name: 'Занятой предприниматель' },
  friendly: { name: 'Дружелюбный' },
} as const;

export const DIFFICULTY = {
  '1': { name: '1 — Лёгкий' },
  '2': { name: '2 — Нормальный' },
  '3': { name: '3 — Сложный' },
  '4': { name: '4 — Очень сложный' },
} as const;

export const PRODUCTS = {
  free: { name: 'Свободная тема' },
  rko: { name: 'РКО' },
  bank_card: { name: 'Бизнес-карта' },
} as const;

export const DEFAULT_SESSION_SETTINGS: SessionSettings = {
  archetype: 'friendly',
  difficulty: '2',
  product: 'free',
};
