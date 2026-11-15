-- Money in and out. Amounts are integer cents (never floats):
--   negative = money spent (-1250 = $12.50 out), positive = money received.
CREATE TABLE transactions (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          bigint      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    category_id      bigint      REFERENCES categories (id) ON DELETE SET NULL,  -- NULL = uncategorized
    posted_date      date        NOT NULL,
    amount_cents     bigint      NOT NULL CHECK (amount_cents <> 0),
    description      text        NOT NULL CHECK (length(btrim(description)) BETWEEN 1 AND 200),
    -- Who chose the category. Only 'user' and 'none' for now; 'rule' and 'llm'
    -- arrive with auto-categorization.
    category_source  text        NOT NULL DEFAULT 'none'
                                 CHECK (category_source IN ('none', 'user', 'rule', 'llm')),
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- Almost every query is "this user's transactions in this date range".
CREATE INDEX transactions_user_date ON transactions (user_id, posted_date);

-- Money received needs a category too. (Added here, not by editing 002:
-- an applied migration is never changed.)
INSERT INTO categories (name) VALUES ('Income');
