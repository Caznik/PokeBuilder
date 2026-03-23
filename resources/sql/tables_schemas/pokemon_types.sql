CREATE TABLE pokemon_types (
    pokemon_id INTEGER,
    type_id INTEGER,
    slot INTEGER NOT NULL,

    PRIMARY KEY (pokemon_id, slot),

    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (type_id) REFERENCES types(id)
);