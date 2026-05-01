CREATE TABLE IF NOT EXISTS saved_team_members (
    id           SERIAL   PRIMARY KEY,
    team_id      INTEGER  NOT NULL REFERENCES saved_teams(id) ON DELETE CASCADE,
    slot         SMALLINT NOT NULL CHECK (slot BETWEEN 0 AND 5),
    pokemon_name TEXT     NOT NULL,
    set_id       INTEGER  NOT NULL REFERENCES competitive_sets(id),
    UNIQUE (team_id, slot)
);
