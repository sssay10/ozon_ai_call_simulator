-- Full database schema and seed data for a fresh Postgres instance.
-- Applied automatically via docker-entrypoint-initdb.d when the data volume is empty.
-- After `DROP DATABASE` / new volume, recreate by restarting Postgres so this script runs again.
-- Application services (judge, auth, agent) do not run migrations; they assume this schema exists.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('manager', 'coach')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

INSERT INTO users (id, email, password_hash, role)
VALUES
    (
        '00000000-0000-0000-0000-000000000101',
        'manager@example.com',
        'pbkdf2_sha256$600000$7b2107ce2bc6ba3df5734a2a521b86f8$0eb95df478ac77e2aab09ed3cc6a127d0699d08d1625c3360b45afad2b640c44',
        'manager'
    ),
    (
        '00000000-0000-0000-0000-000000000102',
        'coach@example.com',
        'pbkdf2_sha256$600000$1aa20de0b878c7a27c35cdf7c2260885$866b8f822f592cceb0dd9d26d004b1e724771fa54918aa77ec5f0e99fcf0fceb',
        'coach'
    )
ON CONFLICT (email) DO NOTHING;

CREATE TABLE IF NOT EXISTS dialogue_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_name TEXT NOT NULL,
    job_id TEXT,
    product TEXT NOT NULL,
    training_scenario_id UUID,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS dialogue_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES dialogue_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dialogue_messages_session_id ON dialogue_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_dialogue_sessions_started_at ON dialogue_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_dialogue_sessions_room_name ON dialogue_sessions(room_name);
CREATE INDEX IF NOT EXISTS idx_dialogue_sessions_owner_user_id ON dialogue_sessions(owner_user_id);

CREATE TABLE IF NOT EXISTS judge_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE REFERENCES dialogue_sessions(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL,
    total_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    critical_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    feedback_positive JSONB NOT NULL DEFAULT '[]'::jsonb,
    feedback_improvement JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    client_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    relevant_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_used TEXT NOT NULL DEFAULT 'unknown',
    judge_backend TEXT NOT NULL DEFAULT 'unknown',
    error TEXT,
    details TEXT,
    raw_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_judge_results_session_id ON judge_results(session_id);

CREATE TABLE IF NOT EXISTS training_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    persona_description TEXT NOT NULL,
    main_pain TEXT NOT NULL DEFAULT '',
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_training_scenarios_updated_at ON training_scenarios(updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_training_scenarios_name ON training_scenarios(name);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_dialogue_sessions_training_scenario_id'
    ) THEN
        ALTER TABLE dialogue_sessions
            ADD CONSTRAINT fk_dialogue_sessions_training_scenario_id
            FOREIGN KEY (training_scenario_id)
            REFERENCES training_scenarios(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_dialogue_sessions_training_scenario_id
    ON dialogue_sessions(training_scenario_id);

-- Preloaded RKO scenarios: novice, expert, skeptic (coach user as author)
INSERT INTO training_scenarios (name, persona_description, main_pain, created_by_user_id)
VALUES
    (
        'RKO / novice',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты только недавно зарегистрировался как продавец на Озон, ты зарегистрирован как ИП.
- Ты полон надежд, но мало понимаешь в финансах, банковских продуктах, тарифах.
- Ты общаешься вежливо, но растерянно. Иногда задаешь простые уточняющие вопросы.$$,
        'Боюсь ошибиться с документами, платежами и налогами на старте.',
        '00000000-0000-0000-0000-000000000102'::uuid
    ),
    (
        'RKO / expert',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты только недавно зарегистрировался как продавец на Озон. Но ты уже предприниматель с опытом, у тебя уже есть расчетный в Т-Банке.
- Ты хорошо разбираешься в банковских продуктах и тарифах.
- Общаешься нейтрально, не очень заинтересовано.$$,
        'Хочу понять, есть ли реально более выгодные условия, чем в моем текущем банке.',
        '00000000-0000-0000-0000-000000000102'::uuid
    ),
    (
        'RKO / skeptic',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты недавно зарегистрировался как продавец на Озон, но не веришь обещаниям банков на слово.
- Ты ожидаешь, что в предложении могут быть скрытые условия, комиссии и ограничения.
- Ты общаешься сдержанно, задаешь уточняющие и проверочные вопросы, часто просишь конкретику и подтверждения.$$,
        'Опасаюсь скрытых условий, комиссий и ограничений.',
        '00000000-0000-0000-0000-000000000102'::uuid
    ),
    (
        'RKO / novice / accounting tools gap',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты новичок на платформе продавцов Озон: зарегистрирован как ИП, уже есть расчетный счет в другом банке.
- Ты торопливый: у тебя мало времени, просишь говорить по делу и коротко, раздражаешься от долгих объяснений.$$,
        'В текущем банке неудобно вести бухгалтерию: сложные выгрузки и слабый контроль налогов.',
        '00000000-0000-0000-0000-000000000102'::uuid
    ),
    (
        'RKO / novice / acquiring tools gap',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты новичок на платформе продавцов Озон: зарегистрирован как ИП, уже работаешь через счет в другом банке.
- Ты сомневающийся: часто переспрашиваешь, опасаешься скрытых комиссий и технических ограничений.
- Общаешься вежливо, но настороженно; хочешь конкретику по срокам, ограничениям и реальным затратам.$$,
        'Не хватает удобного эквайринга: подключение и прием оплат слишком неудобные и медленные.',
        '00000000-0000-0000-0000-000000000102'::uuid
    ),
    (
        'RKO / novice / no foreign incoming payments',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты новичок на платформе продавцов Озон: зарегистрирован как ИП, уже есть расчетный счет в другом банке.
- Ты более агрессивный и немного токсичный в коммуникации: можешь говорить резко, если слышишь расплывчатые ответы.
- Ты требуешь конкретики по ограничениям, срокам и рискам.$$,
        'Не могу получать платежи из-за границы в текущем банке, из-за этого теряю выручку.',
        '00000000-0000-0000-0000-000000000102'::uuid
    ),
    (
        'RKO / novice / savings account interest',
        $$Твое поведение основано на следующем описании характерных черт твой личности и ситуации:
- Ты новичок на платформе продавцов Озон: зарегистрирован как ИП, расчетный счет у тебя уже есть.
- Ты рациональный и въедливый: спокойно общаешься, но задаешь много уточняющих вопросов и просишь объяснить механику без маркетинговых формулировок.
- Если ответ звучит слишком общо, ты возвращаешься к конкретике: условиям, ограничениям, срокам и практическим примерам.$$,
        'Хочу использовать накопительный счет для свободных остатков и понимать реальные условия доходности и налогов.',
        '00000000-0000-0000-0000-000000000102'::uuid
    )
ON CONFLICT (name) DO UPDATE SET
    persona_description = EXCLUDED.persona_description,
    main_pain = EXCLUDED.main_pain,
    updated_at = now();
