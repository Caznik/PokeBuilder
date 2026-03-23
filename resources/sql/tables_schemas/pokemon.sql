CREATE TABLE pokemon (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    generation INTEGER,

    base_hp INTEGER NOT NULL,
    base_attack INTEGER NOT NULL,
    base_defense INTEGER NOT NULL,
    base_sp_attack INTEGER NOT NULL,
    base_sp_defense INTEGER NOT NULL,
    base_speed INTEGER NOT NULL
);