# budget_app

A simple budgeting app with an AI agent, built as a learning project.

> **Status:** the backend MVP (categories, transactions, budgets, dashboard)
> and the frontend pages (welcome, dashboard, transactions, budgets) are built
> and tested; there is no login yet, every request acts as a fake **demo user**.
> **Next:** login (see [Next steps](#next-steps)).

## Running locally

Needs Docker Desktop, Python 3.14 and Node 26.

```bash
cp .env.example .env              # first time only; then set a real password
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

Fake data for the demo user (3 months of transactions and budgets; replaces
only the demo user's data, safe to rerun):

```bash
cd backend && .venv/bin/python -m app.seed
```

## API

All amounts are **integer cents** (negative = spent, positive = received);
months are `"2026-11"`. Interactive docs: http://127.0.0.1:8000/docs

| Method | Endpoint | Does |
|---|---|---|
| GET | `/health` | Backend + database status (503 if the DB is down) |
| GET, POST | `/api/categories` | List defaults + own / create (409 if the name exists) |
| GET | `/api/transactions?month=2026-11` | A month's transactions, newest first |
| POST | `/api/transactions` | Create |
| PUT, DELETE | `/api/transactions/{id}` | Edit / delete |
| GET | `/api/budgets?month=2026-11` | A month's budgets |
| PUT | `/api/budgets` | Set a category's limit for a month (creates or replaces) |
| DELETE | `/api/budgets/{id}` | Remove a budget |
| GET | `/api/dashboard?month=2026-11` | Income, spending, and spending vs budget per category |

Errors: 404 not found (also when it belongs to another user), 409 duplicate,
422 invalid input; the body is `{"detail": "..."}`.

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
│   │   ├── db.py             Postgres connection pool
│   │   ├── config.py         settings read from environment variables
│   │   ├── dependencies.py   builds services; get_current_user_id() (demo user for now)
│   │   ├── errors.py         NotFound / InvalidInput / Conflict (raised by services)
│   │   ├── months.py         "2026-11" <-> date helpers
│   │   ├── migrate.py        applies migrations/*.sql
│   │   ├── seed.py           fake data for the demo user
│   │   ├── routers/          HTTP: health, categories, transactions, budgets, dashboard
│   │   ├── services/         business rules (dashboard math in build_dashboard())
│   │   ├── repositories/     SQL, always filtered by user_id
│   │   └── agent/            empty for now; see its README
│   ├── migrations/           numbered .sql files that create/change tables
│   ├── tests/
│   └── requirements.txt
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
| Login | Not yet: `get_current_user_id()` returns a demo user | Build the app first; real login replaces only that function |
| Refunds | Dashboard uses net per category | A $25 refund lowers that category's spending |
| Look | Dark; phones get a floating bottom nav, desktops (960px+) a sidebar and two-column pages | Follows the Dribbble budget-app shot we picked |
| Responsive layout | One set of components; CSS decides the layout (phone < 960px, icon rail 960–1199px, full sidebar 1200px+) | No separate desktop pages to keep in sync |
| Category colors | 8 fixed colors, one per default category; gray for the rest | Chosen so neighbors stay apart for color-blind readers; shown as soft tints on the light theme, with a deeper shade for icons and names; the same color means the same category on every page |
| "Spent vs. last month" | Same days of last month while a month is still running | Half a month always looks cheaper than a whole one |
| Pages and URLs | React Router; the month is shared state, not in the URL | Switching pages keeps the month you picked |
| Icons and font | `lucide-react`, Urbanist (self-hosted via `@fontsource`) | No requests to font or icon CDNs |

## Next steps

1. ~~**Frontend pages**~~: done. Welcome, Dashboard, Transactions (add, edit,
   delete), Budgets (set limits, new categories), a shared month picker.
2. **Login** (next): replace `get_current_user_id()` in `backend/app/dependencies.py`
   with real auth (argon2 password hashes, server-side sessions in an httpOnly
   cookie, rate limiting on login). Everything else already takes `user_id`
   from there. **Required before a public deploy**: without it, anyone with the
   URL is the demo user.
3. **Deploy on AWS**: one EC2 server with Docker Compose and Caddy (HTTPS), like
   job-tracker. Until login exists, only reachable from the owner's IP.
4. **AI, the main goal of the project**, using **Amazon Bedrock** as the model
   provider: auto-categorization (rules first, LLM for unknown merchants) and a
   chat agent that calls services and needs confirmation before any change.
   - The server gets Bedrock access through an **IAM role**: no API key in `.env`.
   - Only `backend/app/agent/llm.py` knows the provider; the tools and the loop
     are our own code (not Bedrock Agents), so switching providers is one file.
   - Check which models Bedrock offers in the chosen region first.
5. **Later**: bank CSV import (worker + dedupe).

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
| Agent tests (fake services, fake LLM) | agent | Wrong tool calls, endless loops | No, and no API cost |
| Component tests (Vitest, fake `fetch`) | frontend | A page state shown wrong, a button not working, the wrong request sent | No backend |
| Unit tests (Vitest) | frontend helpers | Money/date formatting, amounts parsed wrong | No |

Most tests are service unit tests (fast, where the rules live); fewer
integration and full-stack tests. Commands are in [Tests](#tests).

## Open questions

- What is the agent for? (decides its first tools)
