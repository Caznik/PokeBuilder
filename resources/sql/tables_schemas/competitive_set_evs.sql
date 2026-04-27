CREATE TABLE competitive_set_evs (
    set_id INTEGER,
    hp INTEGER DEFAULT 0,
    attack INTEGER DEFAULT 0,
    defense INTEGER DEFAULT 0,
    sp_attack INTEGER DEFAULT 0,
    sp_defense INTEGER DEFAULT 0,
    speed INTEGER DEFAULT 0,
    PRIMARY KEY (set_id),
    FOREIGN KEY (set_id) REFERENCES competitive_sets(id)
);