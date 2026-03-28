CREATE TABLE natures (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    increased_stat TEXT,
    decreased_stat TEXT
);
