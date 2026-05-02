-- resources/sql/migrations/add_member_detail_columns.sql
-- Adds editable per-member fields to saved_team_members.
-- nature_override / ability_override shadow the competitive_set JOIN values
-- when non-NULL (read with COALESCE in _load_members).
ALTER TABLE saved_team_members
  ADD COLUMN item             TEXT,
  ADD COLUMN tera_type        TEXT,
  ADD COLUMN evs              JSONB,
  ADD COLUMN moves            JSONB,
  ADD COLUMN nature_override  TEXT,
  ADD COLUMN ability_override TEXT;
