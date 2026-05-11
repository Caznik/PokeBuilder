-- OAuth-only users have no password; make the column nullable
ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;

-- Store Google's stable 'sub' identifier for OAuth-linked accounts
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE;
