ALTER TABLE saved_teams
    ADD COLUMN IF NOT EXISTS regulation_id INT
        REFERENCES regulations(id) ON DELETE SET NULL;
