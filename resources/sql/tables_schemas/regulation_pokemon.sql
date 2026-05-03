CREATE TABLE IF NOT EXISTS regulation_pokemon (
    regulation_id INTEGER NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
    pokemon_id    INTEGER NOT NULL REFERENCES pokemon(id)     ON DELETE CASCADE,
    PRIMARY KEY (regulation_id, pokemon_id)
);
