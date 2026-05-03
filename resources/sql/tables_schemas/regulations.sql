CREATE TABLE IF NOT EXISTS regulations (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);
