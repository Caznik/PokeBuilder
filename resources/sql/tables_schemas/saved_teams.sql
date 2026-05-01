CREATE TABLE IF NOT EXISTS saved_teams (
    id          SERIAL PRIMARY KEY,
    name        TEXT            NOT NULL,
    score       NUMERIC(5, 2)   NOT NULL,
    breakdown   JSONB           NOT NULL,
    analysis    JSONB           NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);
