CREATE TABLE type_effectiveness (
    attacker_type_id INTEGER,
    defender_type_id INTEGER,
    multiplier REAL NOT NULL,
    PRIMARY KEY (attacker_type_id, defender_type_id),
    FOREIGN KEY (attacker_type_id) REFERENCES types(id),
    FOREIGN KEY (defender_type_id) REFERENCES types(id)
);
