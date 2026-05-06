-- Migration: add ON DELETE CASCADE to competitive_set_moves and competitive_set_evs
-- Without this, deleting a competitive_set row fails if child rows exist.

ALTER TABLE competitive_set_moves
    DROP CONSTRAINT competitive_set_moves_set_id_fkey,
    ADD CONSTRAINT competitive_set_moves_set_id_fkey
        FOREIGN KEY (set_id) REFERENCES competitive_sets(id) ON DELETE CASCADE;

ALTER TABLE competitive_set_evs
    DROP CONSTRAINT competitive_set_evs_set_id_fkey,
    ADD CONSTRAINT competitive_set_evs_set_id_fkey
        FOREIGN KEY (set_id) REFERENCES competitive_sets(id) ON DELETE CASCADE;
