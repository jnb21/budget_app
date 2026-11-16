# budget_app

A simple budgeting app with an AI agent, built as a learning project.

> **Status:** the app works end to end without AI: login (sign up, log in,
> log out), categories, transactions, budgets, a dashboard, and an account page
> (download my data, delete my account). Light theme. Row-level security in
> Postgres and rate limits on the API. **Next:** deploy on AWS,
> then the AI with Amazon Bedrock (see [Next steps](#next-steps)).

## Running locally

Needs Docker Desktop, Python 3.14 and Node 26.

```bash
cp .env.example .env              # first time only; then set two real passwords
docker compose up -d              # Postgres on 127.0.0.1:5433

cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first time only
.venv/bin/uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs

cd frontend                       # in a second terminal
npm install                       # first time only
npm run dev                       # http://localhost:5173
```

The backend applies database migrations automatically at startup
(or by hand: `.venv/bin/python -m app.migrate`).

### Two database logins

| Setting | Login | May |
|---|---|---|
| `MIGRATION_DATABASE_URL` | the owner (`budget`, created by Docker) | create and change tables and rules: migrations only |
| `DATABASE_URL` | the app (`budget_app`) | read and write rows, nothing else |

Why: Postgres **row-level security** (migration 006) only lets a request see
and change its own user's rows, but owners and superusers skip it silently.
So the running app uses a login with no such powers, and refuses to start if
`DATABASE_URL` is an owner, a superuser or a `BYPASSRLS` role. Migrations
create the `budget_app` login with the password from `DATABASE_URL`, so the
password lives only in `.env`.

In production, give `MIGRATION_DATABASE_URL` to the migration step
(`python -m app.migrate`) and leave it out of the running app's environment:
the app then skips migrating at startup and never holds the owner's password.

Fake data for the demo user (3 months of transactions and budgets; replaces
only the demo user's data, safe to rerun):

```bash
cd backend && .venv/bin/python -m app.seed
```

Then log in at http://localhost:5173 as `demo@budget.local` / `demo-password`.
**Local only:** never run the seed script against a database real people use.

## API

All amounts are **integer cents** (negative = spent, positive = received);
months are `"2026-11"`. Interactive docs: http://127.0.0.1:8000/docs

| Method | Endpoint | Does |
|---|---|---|
| GET | `/health` | Backend + database status (503 if the DB is down). Public |
| POST | `/api/auth/signup` | Create an account and log in (sets the session cookie). 5 per hour per IP |
| POST | `/api/auth/login` | Log in (401 wrong email or password). 429 after 5 failures for one email in 15 min, or 20 tries from one IP |
| POST | `/api/auth/logout` | End the session |
| GET | `/api/auth/me` | Who is logged in (401 if nobody) |
| GET | `/api/account/export` | Everything stored about you, as JSON |
| POST | `/api/account/delete` | Delete your account and all your data (needs `{"password"}`). 5 tries per 15 min |
| PUT, DELETE | `/api/categories/{id}` | Rename / delete one of your own categories |
| GET, POST | `/api/categories` | List defaults + own / create (409 if the name exists) |
| GET | `/api/transactions?month=2026-11` | A month's transactions, newest first |
| POST | `/api/transactions` | Create |
| PUT, DELETE | `/api/transactions/{id}` | Edit / delete |
| GET | `/api/budgets?month=2026-11` | A month's budgets |
| PUT | `/api/budgets` | Set a category's limit for a month (creates or replaces) |
| DELETE | `/api/budgets/{id}` | Remove a budget |
| GET | `/api/dashboard?month=2026-11` | Income, spending, and spending vs budget per category |

Everything under `/api/` except `/api/auth/*` needs a login. The session is a
random token in an **httpOnly, SameSite=Lax** cookie; the database stores only
its SHA-256 hash. Passwords are hashed with argon2.

Errors: 401 not logged in, 404 not found (also when it belongs to another
user), 409 duplicate, 422 invalid input, 429 too many requests (with a
`Retry-After` header in seconds); the body is `{"detail": "..."}`.

### Rate limits

Token buckets in memory (`app/rate_limit.py`): each caller's bucket holds up to
N tokens and refills steadily; each request takes one; an empty bucket → 429.

| What | Burst | Refill | Counted per |
|---|---|---|---|
| Every `/api` request | 100 | 100 per minute | user when logged in, IP otherwise |
| Log in | 20 | 20 per 15 min | IP (IPv6: per /64 block) |
| Sign up | 5 | 5 per hour | IP |
| Delete account | 5 | 5 per 15 min | user |

Plus the stored limit of 5 failed logins per email per 15 minutes
(`login_failures` table). The buckets reset when the server restarts and
aren't shared between servers, which is fine for one server. Behind Caddy,
start uvicorn with `--proxy-headers --forwarded-allow-ips=<Caddy's IP>`, or
every request looks like it comes from Caddy (one shared bucket).

## Tests

```bash
cd backend && .venv/bin/pytest            # needs the Postgres container running
cd frontend && npm test                   # no backend needed
```

## Architecture

```
frontend → routers → services → repositories → Postgres
                ↓        ↑
          /agent router  │
                ↓        │
             agent/ ─────┘   (calls services, never repositories)
```

Each layer only calls the one below it:

1. **routers**: HTTP only. Parse the request, call a service, return the response.
2. **services**: business rules (for example, "a budget can't be negative").
3. **repositories**: SQL only. The only code that talks to Postgres.
4. **agent**: the agentic work (LLM loop, tools, prompts). Its tools call
   **services**, so the agent follows the same rules and per-user filtering as
   the UI. A test will fail if `agent/` imports from `repositories/`.

## Structure

```
budget_app/
├── frontend/
│   └── src/
│       ├── main.jsx          starts the app: router + shared month
│       ├── App.jsx           page URLs (/welcome, /dashboard, /transactions, /budgets, /status)
│       ├── api.js            every call to the backend; errors become readable messages
│       ├── pages/            one file per page, each with its .test.jsx
│       ├── components/       shared pieces: Money, MonthPicker, Sheet (modal), forms, charts
│       ├── money.js          cents <-> "$1,475.00"; parses what the user types
│       ├── months.js         "2026-11" helpers, local dates
│       ├── categories.js     each category's color and icon
│       ├── index.css         design tokens (colors, radii, font)
│       ├── App.css           component styles; the desktop layout is at the end
│       └── test/             fake fetch, sample API answers, test setup
├── backend/
│   ├── app/
│   │   ├── main.py           creates the FastAPI app, plugs in routers, maps errors to HTTP codes
│   │   ├── db.py             Postgres connection pool; get_connection(user_id) for row-level security
│   │   ├── config.py         settings read from environment variables
│   │   ├── dependencies.py   builds services; get_current_user_id() reads the session cookie
│   │   ├── errors.py         NotFound / InvalidInput / Conflict / ... (raised by services)
│   │   ├── rate_limit.py     token buckets for the rate limits
│   │   ├── months.py         "2026-11" <-> date helpers
│   │   ├── migrate.py        applies migrations/*.sql as the owner; creates the app's login
│   │   ├── seed.py           fake data for the demo user
│   │   ├── routers/          HTTP: health, auth (login, account), categories, transactions, budgets, dashboard
│   │   ├── services/         business rules (dashboard math in build_dashboard())
│   │   ├── repositories/     SQL, always filtered by user_id (and RLS behind it)
│   │   └── agent/            empty for now; see its README
│   ├── migrations/           numbered .sql files that create/change tables
│   ├── tests/
│   └── requirements.txt
├── deploy/                   AWS: setup.sh (once), deploy.sh (each release), cloudformation.yml,
│   └── server/               what runs on the server: compose.yml, Caddyfile, update.sh, backup.sh
├── docs/aws-architecture.html  the AWS plan, with diagrams
├── docker-compose.yml        Postgres for local development
└── README.md
```

## Decisions

| Topic | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Same as the job tracker; best AI/agent libraries |
| Frontend | React + Vite | Same as the job tracker; simple setup |
| Database | Postgres, plain SQL with `psycopg` | See the real SQL; no ORM to learn on top |
| Schema changes | Numbered `.sql` migrations | Every database change is recorded and repeatable |
| Agent | Inside the backend, calls services | One path to the data, so rules and permissions always apply |
| Money | Integer cents (`bigint`) | Floats cause rounding errors (`0.1 + 0.2 != 0.3`) |
| Users | `user_id` on every table, every query filtered by it | Isolation; 404 (not 403) for other users' rows so nothing leaks |
| Row-level security | On `transactions`, `budgets`, `categories`; the app connects as a login that can't skip it | A second lock: a query that forgets its user filter still sees nothing of other users. Auth tables stay outside it (login must find a user before anyone is known) |
| Rate limiting | Own token buckets in memory, no library | ~70 readable lines; one server doesn't need Redis. AWS WAF would need a load balancer or CloudFront in front |
| Login | Own accounts: argon2 passwords, server-side sessions in an httpOnly cookie | No outside provider; logout ends a session immediately (unlike a JWT); a stolen database gives neither passwords nor live sessions |
| Refunds | Dashboard uses net per category | A $25 refund lowers that category's spending |
| Look | Dark; phones get a floating bottom nav, desktops (960px+) a sidebar and two-column pages | Follows the Dribbble budget-app shot we picked |
| Responsive layout | One set of components; CSS decides the layout (phone < 960px, icon rail 960–1199px, full sidebar 1200px+) | No separate desktop pages to keep in sync |
| Category colors | 8 fixed colors, one per default category; gray for the rest | Chosen so neighbors stay apart for color-blind readers; shown as soft tints on the light theme, with a deeper shade for icons and names; the same color means the same category on every page |
| "Spent vs. last month" | Same days of last month while a month is still running | Half a month always looks cheaper than a whole one |
| Pages and URLs | React Router; the month is shared state, not in the URL | Switching pages keeps the month you picked |
| Icons and font | `lucide-react`, Urbanist (self-hosted via `@fontsource`) | No requests to font or icon CDNs |
| AWS setup | One CloudFormation template + two shell scripts, in us-east-1 | Only the AWS CLI and Docker needed; the whole setup is one readable file. CloudFront's certificate must be in us-east-1 anyway |
| Deploys | From your laptop: image to ECR, server updated through SSM Run Command | No SSH port, no AWS keys on the server; GitHub Actions can run the same steps later |
| Visitor IP behind CloudFront | A CloudFront Function writes `X-Viewer-Ip`; Caddy passes it on as `X-Forwarded-For` | The rate limits keep working with no app change, and visitors can't fake it |
| Postgres in production | On the server, data on its own EBS disk; nightly `pg_dump` to S3 + daily snapshots | Cheapest for phase 1, and the disk survives a server replacement. RDS comes with a second server |

## Next steps

1. ~~Frontend pages~~ and ~~login~~: done.
2. **Deploy on AWS** (next): ready to run, see **[`deploy/README.md`](deploy/README.md)**
   (one `setup.sh`, then `deploy.sh` per release; plan and diagrams in
   [`docs/aws-architecture.html`](docs/aws-architecture.html)). Route 53 →
   CloudFront, which serves the app from a private S3 bucket and sends `/api/*`
   to one EC2 server (Caddy, API and Postgres in Docker Compose; only CloudFront
   can reach it). It already sets `COOKIE_SECURE=true`, runs migrations as a
   separate step with the owner login, and passes the visitor's real IP to the
   rate limits. Never run the seed script there.
3. **AI, the main goal of the project**, using **Amazon Bedrock** as the model
   provider: auto-categorization (rules first, LLM for unknown merchants) and a
   chat agent that calls services and needs confirmation before any change.
   - The server gets Bedrock access through an **IAM role**: no API key in `.env`.
   - Only `backend/app/agent/llm.py` knows the provider; the tools and the loop
     are our own code (not Bedrock Agents), so switching providers is one file.
   - Check which models Bedrock offers in the chosen region first.
4. **Later**: bank CSV import (worker + dedupe).

## Testing

Claude writes the tests; for each one it explains what risk it covers, which
kind of test it is, and how to read it. Every test follows **Arrange → Act → Assert**.

| Kind | Layer | What it catches | Database? |
|---|---|---|---|
| Unit tests (fake repository) | services | Wrong business rules | No |
| Integration tests (`budget_test` DB) | repositories | Wrong SQL, data leaking between users | Yes, real Postgres |
| API tests (FastAPI `TestClient`) | routers | Wrong status codes, bad input accepted | Sometimes |
| Full-stack tests (`TestClient` + real DB) | `main.py` | Layers not wired together, startup/shutdown | Yes |
| Architecture tests (read the source) | agent | `agent/` importing repositories or the DB | No |
| Row-level security tests (raw SQL as the app's login) | database | A user reaching another user's rows even without a `WHERE user_id`; a new table missing its rules | Yes |
| Agent tests (fake services, fake LLM) | agent | Wrong tool calls, endless loops | No, and no API cost |
| Component tests (Vitest, fake `fetch`) | frontend | A page state shown wrong, a button not working, the wrong request sent | No backend |
| Unit tests (Vitest) | frontend helpers | Money/date formatting, amounts parsed wrong | No |

Most tests are service unit tests (fast, where the rules live); fewer
integration and full-stack tests. Commands are in [Tests](#tests).

## Open questions

- What is the agent for? (decides its first tools)
