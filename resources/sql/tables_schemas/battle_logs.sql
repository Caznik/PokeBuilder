-- Battle logs: user-recorded manual battle results
CREATE TABLE IF NOT EXISTS battle_logs (
    id              SERIAL PRIMARY KEY,
    user_id         INT         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    saved_team_id   INT         REFERENCES saved_teams(id) ON DELETE SET NULL,
    regulation_id   INT         REFERENCES regulations(id) ON DELETE SET NULL,
    format          TEXT        NOT NULL CHECK (format IN ('singles', 'vgc')),
    brought_pokemon TEXT[]      NOT NULL,
    enemy_team      TEXT[]      NOT NULL,
    result          TEXT        NOT NULL CHECK (result IN ('win', 'loss', 'tie')),
    notes           TEXT,
    played_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
