-- -----------------------------------------------
-- NOVA IntentOS — Database Schema
-- -----------------------------------------------

-- Workspaces (empresas/usuarios)
CREATE TABLE IF NOT EXISTS workspaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    api_key     TEXT UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex'),
    plan        TEXT DEFAULT 'trial',  -- trial, shield, professional, enterprise
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Intent Tokens (el contrato del agente)
CREATE TABLE IF NOT EXISTS intent_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_name      TEXT NOT NULL,
    description     TEXT,
    can_do          TEXT[],           -- Lista de lo que SÍ puede hacer
    cannot_do       TEXT[],           -- Lista de lo que NO puede hacer
    authorized_by   TEXT NOT NULL,    -- Email del humano que firmó
    signature       TEXT NOT NULL,    -- SHA-256 del token
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Ledger de Acciones (inmutable — nunca se actualiza, solo INSERT)
CREATE TABLE IF NOT EXISTS ledger (
    id              BIGSERIAL PRIMARY KEY,
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    token_id        UUID REFERENCES intent_tokens(id),
    agent_name      TEXT NOT NULL,
    action          TEXT NOT NULL,    -- La acción que el agente quería hacer
    context         TEXT,             -- Contexto adicional (email, datos, etc)
    score           INTEGER NOT NULL, -- 0-100 Intent Fidelity Score
    verdict         TEXT NOT NULL,    -- APPROVED | BLOCKED | ESCALATED
    reason          TEXT,             -- Por qué ese score
    prev_hash       TEXT,             -- Hash del registro anterior (cadena)
    own_hash        TEXT NOT NULL,    -- Hash de este registro
    executed_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Alertas
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    ledger_id       BIGINT REFERENCES ledger(id),
    agent_name      TEXT NOT NULL,
    message         TEXT NOT NULL,
    score           INTEGER,
    resolved        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_ledger_workspace ON ledger(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ledger_token ON ledger(token_id);
CREATE INDEX IF NOT EXISTS idx_ledger_score ON ledger(score);
CREATE INDEX IF NOT EXISTS idx_alerts_workspace ON alerts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved);

-- Demo workspace para empezar
INSERT INTO workspaces (name, email, api_key, plan)
VALUES ('Mi Empresa Demo', 'demo@nova.io', 'nova_demo_key_12345', 'professional')
ON CONFLICT (email) DO NOTHING;