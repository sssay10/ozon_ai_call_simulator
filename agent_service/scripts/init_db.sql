-- Dialogue logging schema for manager quality and analytics.
-- Runs once when Postgres container is first created (docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('manager', 'coach')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
    archetype TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    product TEXT NOT NULL,
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
