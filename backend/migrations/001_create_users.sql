-- Everyone who uses the app. Every budget, category and transaction will
-- belong to one user (a user_id column pointing here).
CREATE TABLE users (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email       text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- One account per email, ignoring case: Alice@Mail.com = alice@mail.com.
CREATE UNIQUE INDEX users_email_unique ON users (lower(email));
