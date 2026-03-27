CREATE TABLE pokemon_moves (
    pokemon_id INTEGER,
    move_id INTEGER,
    learn_method TEXT,  -- level-up / machine / tutor
    level INTEGER,      -- nullable
    PRIMARY KEY (pokemon_id, move_id, learn_method),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (move_id) REFERENCES moves(id)
);