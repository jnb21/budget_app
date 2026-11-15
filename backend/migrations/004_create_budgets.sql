-- A monthly spending limit for one category.
CREATE TABLE budgets (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      bigint      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    category_id  bigint      NOT NULL REFERENCES categories (id) ON DELETE CASCADE,
    month        date        NOT NULL CHECK (extract(day FROM month) = 1),  -- always the 1st: 2026-11-01
    limit_cents  bigint      NOT NULL CHECK (limit_cents > 0),
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, category_id, month)  -- one limit per category per month
);
