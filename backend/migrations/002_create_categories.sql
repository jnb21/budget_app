-- Spending categories (Groceries, Rent, ...).
-- user_id NULL  = a default category everyone sees.
-- user_id set   = a category that one user created for themselves.
CREATE TABLE categories (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     bigint      REFERENCES users (id) ON DELETE CASCADE,
    name        text        NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 50),
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- No two default categories with the same name, ignoring case...
CREATE UNIQUE INDEX categories_default_name_unique
    ON categories (lower(name)) WHERE user_id IS NULL;

-- ...and no user has two categories with the same name.
CREATE UNIQUE INDEX categories_user_name_unique
    ON categories (user_id, lower(name)) WHERE user_id IS NOT NULL;

INSERT INTO categories (name) VALUES
    ('Groceries'),
    ('Rent'),
    ('Utilities'),
    ('Transport'),
    ('Dining out'),
    ('Entertainment'),
    ('Health'),
    ('Shopping'),
    ('Other');
