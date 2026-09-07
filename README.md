# TouchGrass

Web app helping residents of low-canopy Melbourne suburbs find and reach tree-dense green
spaces, using City of Melbourne Urban Forest open data.

Group 44 — Iteration 1 scaffold.

## Layout

```
frontend/   Vue 3 + Vite + TypeScript + Pinia
backend/    FastAPI (Python), containerised for Cloud Run
docker-compose.yml   local PostGIS
.github/workflows/   CI: format, lint, build
```

## Requirements

Node 20+, Python 3.12+, Docker (only needed for the local database).

## Run it

Two terminals.

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

Check http://localhost:8080/health — it should return `{"status":"ok",...}`.
Interactive API docs are at http://localhost:8080/docs.

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:5173. The home page calls `/health`; if it says the backend is
connected, both halves are wired up correctly.

**Database (optional until the data pipeline starts)**

```bash
docker compose up -d db
```

Postgres 16 with PostGIS on port 5432, credentials in `docker-compose.yml`.
Nothing connects to it yet — the backend has no database code until the schema is agreed.

## Checks before pushing

```bash
cd frontend && npm run format && npm run lint && npm run build
cd backend  && black . && ruff check .
```

CI runs the same commands on every pull request.

## Branching

```
Trello card → feature branch → local checks → pull request → one review → merge
```

```bash
git switch main
git pull
git switch -c feature/US1.1-canopy-density
# work, then
git add -A
git commit -m "US1.1 add canopy density layer"
git push -u origin feature/US1.1-canopy-density
```

Open the pull request on GitHub, link the Trello card, request one reviewer.
Nobody pushes to `main` directly.

## Not decided yet

Deliberately absent from this scaffold, because the decisions are still open:

- Database schema and models — no ORM or migrations wired in.
- API endpoints beyond `/health` — the contract is owned by IT and not yet agreed.
- Test frameworks — no test job in CI yet.
- Cloud deployment — no Firebase or Cloud Run deploy workflow. Local only for now.
- Authentication.

Add each one in its own pull request once the team confirms it, and record the decision
in the Technology Stack decision log.

## Secrets

`.env` and `.env.local` are gitignored and must stay that way. Only `.env.example` is
committed, with variable names and no values. Paid Google APIs are called from the
backend; the browser only ever holds a referrer-restricted Maps key.
