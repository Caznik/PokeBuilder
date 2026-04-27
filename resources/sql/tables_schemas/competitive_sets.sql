CREATE TABLE competitive_sets (
    id SERIAL PRIMARY KEY,
    pokemon_id INTEGER NOT NULL,
    name TEXT, -- e.g. "Choice Scarf", "Defensive"
    nature_id INTEGER,
    ability_id INTEGER,
    item TEXT,
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (nature_id) REFERENCES natures(id),
    FOREIGN KEY (ability_id) REFERENCES abilities(id)
);