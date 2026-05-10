CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
    id               SERIAL PRIMARY KEY,
    ingestor         TEXT UNIQUE NOT NULL,
    last_run_at      TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01 00:00:00+00',
    replays_ingested INT NOT NULL DEFAULT 0
);
