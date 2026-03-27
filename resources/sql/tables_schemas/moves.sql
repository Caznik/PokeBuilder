CREATE TABLE moves (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type_id INTEGER NOT NULL,
    power INTEGER,
    accuracy INTEGER,
    pp INTEGER,
    category_id INTEGER NOT NULL, -- physical / special / status
    effect TEXT,
    FOREIGN KEY (type_id) REFERENCES types(id),
    FOREIGN KEY (category_id) REFERENCES move_categories(id)
);