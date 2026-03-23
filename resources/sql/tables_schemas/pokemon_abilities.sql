CREATE TABLE pokemon_abilities (
    pokemon_id INTEGER,
    ability_id INTEGER,
    is_hidden BOOLEAN DEFAULT FALSE,

    PRIMARY KEY (pokemon_id, ability_id),

    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (ability_id) REFERENCES abilities(id)
);