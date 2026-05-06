-- Migration: add format column to competitive_sets
-- Stores the Smogon strategy format (e.g. "OU", "VGC 2025 Reg G", "Doubles OU").
-- NULL for sets ingested before this migration.
ALTER TABLE competitive_sets ADD COLUMN IF NOT EXISTS format TEXT;
