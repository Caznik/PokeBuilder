-- Add enemy_brought column to battle_logs
-- Tracks which Pokémon the opponent chose to bring (subset of enemy_team)
ALTER TABLE battle_logs
    ADD COLUMN IF NOT EXISTS enemy_brought TEXT[] NOT NULL DEFAULT '{}';
