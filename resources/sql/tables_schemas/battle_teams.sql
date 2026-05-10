CREATE TABLE IF NOT EXISTS battle_teams (
    id         SERIAL PRIMARY KEY,
    replay_id  TEXT NOT NULL REFERENCES battle_replays(id) ON DELETE CASCADE,
    player     TEXT NOT NULL CHECK (player IN ('p1', 'p2')),
    team       TEXT[] NOT NULL,
    brought    TEXT[] NOT NULL,
    leads      TEXT[] NOT NULL,
    UNIQUE (replay_id, player)
);
