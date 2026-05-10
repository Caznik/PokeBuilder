CREATE TABLE IF NOT EXISTS battle_pokemon_details (
    id         SERIAL PRIMARY KEY,
    replay_id  TEXT NOT NULL REFERENCES battle_replays(id) ON DELETE CASCADE,
    player     TEXT NOT NULL CHECK (player IN ('p1', 'p2')),
    pokemon    TEXT NOT NULL,
    moves      TEXT[] NOT NULL DEFAULT '{}',
    item       TEXT,
    ability    TEXT,
    UNIQUE (replay_id, player, pokemon)
);
