CREATE TABLE move_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO move_categories (id, name) VALUES
(1, 'physical'),
(2, 'special'),
(3, 'status');