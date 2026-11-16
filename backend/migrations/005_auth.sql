-- Login. Existing users (the demo user) get no password: they can't log in
-- until one is set (the seed script sets the demo user's, for local use).
ALTER TABLE users ADD COLUMN password_hash text;

-- One row per logged-in browser. The cookie holds a random token; only its
-- SHA-256 hash is stored, so a leaked database can't be used to log in.
CREATE TABLE sessions (
    token_hash  text        PRIMARY KEY,
    user_id     bigint      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL
);
CREATE INDEX sessions_user ON sessions (user_id);

-- Failed logins, for rate limiting (too many in a short time -> wait).
CREATE TABLE login_failures (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         text        NOT NULL,
    attempted_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX login_failures_email_time ON login_failures (lower(email), attempted_at);
