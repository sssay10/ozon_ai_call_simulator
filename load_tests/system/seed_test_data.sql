-- Seed data for E2E load test.
-- Inserted after init.sql by docker-entrypoint-initdb.d (alphabetical order).
-- Contains: a dedicated load-test user, pre-built dialogue sessions, and
-- cached judge_results so JudgeUser tests DB reads without re-running LLM.

-- ── Load-test user ────────────────────────────────────────────────────────
-- password: testpass123
-- hash: pbkdf2_sha256$600000$aabbccddeeff0011aabbccddeeff0011$8395e4955309f28d68a491526f3c933f3b89fd5c3c9d1f866bc4eb58e8753912
INSERT INTO users (id, email, password_hash, role)
VALUES (
    '00000000-0000-0000-0000-000000009001'::uuid,
    'loadtest@example.com',
    'pbkdf2_sha256$600000$aabbccddeeff0011aabbccddeeff0011$8395e4955309f28d68a491526f3c933f3b89fd5c3c9d1f866bc4eb58e8753912',
    'manager'
)
ON CONFLICT (email) DO NOTHING;

-- ── Pre-seeded dialogue sessions ─────────────────────────────────────────
INSERT INTO dialogue_sessions (id, room_name, job_id, product, owner_user_id, started_at, ended_at)
VALUES
    (
        '11000000-0000-0000-0000-000000000001'::uuid,
        'load-test-room-001', 'load-job-001',
        'RKO',
        '00000000-0000-0000-0000-000000009001'::uuid,
        now() - interval '10 minutes',
        now() - interval '5 minutes'
    ),
    (
        '11000000-0000-0000-0000-000000000002'::uuid,
        'load-test-room-002', 'load-job-002',
        'RKO',
        '00000000-0000-0000-0000-000000009001'::uuid,
        now() - interval '20 minutes',
        now() - interval '15 minutes'
    ),
    (
        '11000000-0000-0000-0000-000000000003'::uuid,
        'load-test-room-003', 'load-job-003',
        'RKO',
        '00000000-0000-0000-0000-000000009001'::uuid,
        now() - interval '30 minutes',
        now() - interval '25 minutes'
    )
ON CONFLICT DO NOTHING;

-- ── Dialogue messages for each session ───────────────────────────────────
INSERT INTO dialogue_messages (session_id, role, content)
VALUES
    ('11000000-0000-0000-0000-000000000001'::uuid, 'assistant',
     'Добро пожаловать в Озон Банк. Меня зовут Алина. Чем могу помочь?'),
    ('11000000-0000-0000-0000-000000000001'::uuid, 'user',
     'Здравствуйте. Хочу узнать про открытие расчётного счёта для ИП.'),
    ('11000000-0000-0000-0000-000000000001'::uuid, 'assistant',
     'Открытие счёта бесплатно и занимает около пяти минут. Вы уже зарегистрированы как ИП?'),
    ('11000000-0000-0000-0000-000000000001'::uuid, 'user',
     'Да, я ИП на УСН. Какие документы нужны?'),
    ('11000000-0000-0000-0000-000000000001'::uuid, 'assistant',
     'Потребуется паспорт и ОГРНИП — больше ничего. Переводы внутри банка мгновенные.'),

    ('11000000-0000-0000-0000-000000000002'::uuid, 'assistant',
     'Здравствуйте, Озон Банк, Алина слушает.'),
    ('11000000-0000-0000-0000-000000000002'::uuid, 'user',
     'Добрый день. У вас есть накопительный счёт для ИП?'),
    ('11000000-0000-0000-0000-000000000002'::uuid, 'assistant',
     'Да, ставка до восьми процентов годовых на остаток. Снять можно в любой момент.'),
    ('11000000-0000-0000-0000-000000000002'::uuid, 'user',
     'А минимальная сумма?'),
    ('11000000-0000-0000-0000-000000000002'::uuid, 'assistant',
     'Минимальная сумма для открытия — одна тысяча рублей.'),

    ('11000000-0000-0000-0000-000000000003'::uuid, 'assistant',
     'Добро пожаловать! Расскажите, чем могу помочь?'),
    ('11000000-0000-0000-0000-000000000003'::uuid, 'user',
     'Меня интересует эквайринг для онлайн-продаж.'),
    ('11000000-0000-0000-0000-000000000003'::uuid, 'assistant',
     'Эквайринг подключается бесплатно. Комиссия от 1.5% в зависимости от оборота.'),
    ('11000000-0000-0000-0000-000000000003'::uuid, 'user',
     'Спасибо, понял.'),
    ('11000000-0000-0000-0000-000000000003'::uuid, 'assistant',
     'Если есть ещё вопросы — всегда рады помочь. Хорошего дня!')
ON CONFLICT DO NOTHING;

-- ── Pre-computed judge_results (cached; refresh=false skips LLM) ──────────
INSERT INTO judge_results (
    session_id, scenario_id, total_score, scores,
    critical_errors, feedback_positive, feedback_improvement,
    recommendations, client_profile, relevant_criteria,
    model_used, judge_backend, raw_result
)
VALUES
    (
        '11000000-0000-0000-0000-000000000001'::uuid,
        'RKO / novice',
        78.5,
        '{"greeting": 90, "needs_identification": 75, "product_presentation": 80, "objection_handling": 70}'::jsonb,
        '[]'::jsonb,
        '["Чёткое приветствие", "Правильно уточнил форму регистрации ИП"]'::jsonb,
        '["Не спросил о текущем банке клиента", "Не предложил накопительный счёт"]'::jsonb,
        '["Использовать воронку потребностей перед презентацией продукта"]'::jsonb,
        '{"type": "novice", "registered": true}'::jsonb,
        '["greeting", "needs_identification", "product_presentation"]'::jsonb,
        'openai/gpt-4o-mini', 'llm_judge',
        '{}'::jsonb
    ),
    (
        '11000000-0000-0000-0000-000000000002'::uuid,
        'RKO / expert',
        85.0,
        '{"greeting": 85, "needs_identification": 90, "product_presentation": 88, "objection_handling": 77}'::jsonb,
        '[]'::jsonb,
        '["Точно ответил на вопрос о накопительном счёте", "Назвал конкретные условия"]'::jsonb,
        '["Не уточнил источник свободных остатков"]'::jsonb,
        '["Предлагать сравнение с текущим банком клиента"]'::jsonb,
        '{"type": "expert", "has_existing_account": true}'::jsonb,
        '["needs_identification", "product_presentation"]'::jsonb,
        'openai/gpt-4o-mini', 'llm_judge',
        '{}'::jsonb
    ),
    (
        '11000000-0000-0000-0000-000000000003'::uuid,
        'RKO / skeptic',
        72.0,
        '{"greeting": 80, "needs_identification": 70, "product_presentation": 72, "objection_handling": 65}'::jsonb,
        '[]'::jsonb,
        '["Корректно объяснил условия эквайринга"]'::jsonb,
        '["Не обработал возможные возражения по комиссии", "Завершил разговор слишком быстро"]'::jsonb,
        '["Задавать уточняющие вопросы об объёме транзакций до называния комиссии"]'::jsonb,
        '{"type": "skeptic", "needs_acquiring": true}'::jsonb,
        '["product_presentation", "objection_handling"]'::jsonb,
        'openai/gpt-4o-mini', 'llm_judge',
        '{}'::jsonb
    )
ON CONFLICT (session_id) DO NOTHING;
