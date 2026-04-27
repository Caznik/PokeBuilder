CREATE TABLE competitive_set_moves (
    set_id INTEGER,
    move_id INTEGER,
    PRIMARY KEY (set_id, move_id),
    FOREIGN KEY (set_id) REFERENCES competitive_sets(id),
    FOREIGN KEY (move_id) REFERENCES moves(id)
);