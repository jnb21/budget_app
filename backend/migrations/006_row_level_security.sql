-- Row-level security (RLS): Postgres itself only lets a request see and
-- change the rows of the user it is for, even if a query forgets its
-- "WHERE user_id = ...". A second lock behind the one in the repositories.
--
-- Who the request is for: db.get_connection(user_id) runs
--     SELECT set_config('app.user_id', '42', true)
-- at the start of each transaction (true = this transaction only, so it
-- can't leak to the next request that borrows the same connection).
--
-- Two logins (README, "Two database logins"): the owner runs this file; the
-- app's login is a member of budget_rw and may only read and write rows.
-- Owners and superusers skip RLS, which is why the app must not be the owner.
-- (migrate.py creates the roles: roles belong to the whole Postgres server,
-- not to one database.)
--
-- Not under RLS: users, sessions, login_failures. Logging in has to find a
-- user by email BEFORE anyone is known, so the auth code guards those.

-- The request's user, or NULL if none was set. NULL matches no row, so a
-- forgotten user_id shows nothing instead of everything. (NULLIF: once a
-- transaction that set it ends, the value is '' rather than gone, and
-- ''::bigint would be an error.)
CREATE FUNCTION app_user_id() RETURNS bigint
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::bigint $$;

-- The app's rights: rows only. No CREATE, ALTER or DROP, and no access to
-- schema_migrations. A new table needs its own GRANT (a test checks this).
GRANT USAGE ON SCHEMA public TO budget_rw;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON users, sessions, login_failures, categories, transactions, budgets
    TO budget_rw;

-- USING: which rows a query can see, update or delete.
-- WITH CHECK: what a row may look like after an insert or update (so nobody
-- can create a row for someone else, or move one of theirs to someone else).
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_rows ON transactions
    USING (user_id = app_user_id())
    WITH CHECK (user_id = app_user_id());

ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_rows ON budgets
    USING (user_id = app_user_id())
    WITH CHECK (user_id = app_user_id());

-- Categories: everyone reads the defaults (user_id NULL); only your own can
-- be created, renamed or deleted.
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY read_defaults_and_own ON categories FOR SELECT
    USING (user_id IS NULL OR user_id = app_user_id());
CREATE POLICY create_own ON categories FOR INSERT
    WITH CHECK (user_id = app_user_id());
CREATE POLICY change_own ON categories FOR UPDATE
    USING (user_id = app_user_id())
    WITH CHECK (user_id = app_user_id());
CREATE POLICY delete_own ON categories FOR DELETE
    USING (user_id = app_user_id());
