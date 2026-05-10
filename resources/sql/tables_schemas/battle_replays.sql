CREATE TABLE IF NOT EXISTS battle_replays (
    id            TEXT PRIMARY KEY,
    regulation_id INT REFERENCES regulations(id) ON DELETE SET NULL,
    p1            TEXT NOT NULL,
    p2            TEXT NOT NULL,
    winner        TEXT NOT NULL CHECK (winner IN ('p1', 'p2')),
    uploaded_at   TIMESTAMPTZ NOT NULL,
    format        TEXT NOT NULL
);
