# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Soft Landing** is a passenger disruption management system for airlines. A gate agent can handle 200+ disrupted passengers in minutes via a real-time dashboard. Three components live in this monorepo:

1. **backend/** — Python 3.14 + FastAPI + async SQLAlchemy + PostgreSQL
2. **dashboard/** — React 19 + TypeScript + Vite + Tailwind CSS 4
3. **passenger-app/** — Kotlin Multiplatform (stub, not yet implemented)

## Common Commands

### Backend (run from `backend/`)

```bash
docker compose up -d                          # Start Postgres
uv sync --python python3.14                   # Install dependencies
uvicorn app.main:app --reload                 # Dev server (port 8000)
uv run pytest                                 # Run all tests
uv run pytest tests/test_disruption_engine.py # Single test file
uv run pytest -k "test_name"                  # Single test by name
```

### Dashboard (run from `dashboard/`)

```bash
npm install     # Install dependencies
npm run dev     # Dev server with HMR
npm run build   # Type-check (tsc -b) then build
npm run lint    # ESLint
```

### Deployment

```bash
bash infra/deploy.sh all        # Deploy everything
bash infra/deploy.sh backend    # Backend only
bash infra/deploy.sh dashboard  # Dashboard only
```

## Architecture

### Backend

- **Entry point:** `app/main.py` — FastAPI app with lifespan that inits DB and auto-seeds snowstorm scenario
- **Models:** `app/models.py` — Pydantic models defining the API contract (Disruption, Passenger, Option, Wish)
- **Store:** `app/store.py` — async CRUD layer mapping ORM rows to Pydantic models
- **DB:** `app/db/engine.py` (async SQLAlchemy engine), `app/db/tables.py` (8 ORM models)
- **WebSocket:** `app/ws.py` — ConnectionManager with per-passenger and per-disruption channels. Envelope format: `{type, timestamp, data}`
- **Services:**
  - `disruption_engine.py` — event classification, affected passenger lookup, option generation orchestration
  - `option_generator.py` — deterministic option creation (rebook, hotel, ground transport, alt-airport)
  - `gemini.py` — Gemini integration with Google Search + Maps grounding
  - `lufthansa.py` — Lufthansa Flight Ops API client with OAuth2 token caching
- **Seeds:** `app/seeds/` — scenario_snowstorm (hub disruption, 150+ pax), scenario_diversion (aircraft malfunction, 30 pax)
- **Tests:** pytest with `asyncio_mode = "auto"`, uses aiosqlite for in-memory test DB

API docs at `/api/docs` (Swagger) and `/api/redoc`.

### Dashboard

- **API layer:** `src/api/` — interface in `index.ts`, with `mock-adapter.ts` (dev) and `api-adapter.ts` (real backend)
- **Types:** `src/types/index.ts` — mirrors backend Pydantic models
- **Two main views:** Flight Overview (passenger grid) and Wish Stream (real-time approve/deny feed)
- **Hooks:** `src/hooks/` — `use-disruption.ts`, `use-wishes.ts` for data fetching

### Data Flow

Disruption event → DisruptionEngine classifies → finds affected passengers → generates options → stores in Postgres → WebSocket pushes to dashboard. Passengers submit wishes (ranked option preferences) → gate agent approves/denies via dashboard → WebSocket notifies passenger.

### Key Domain Types

- **DisruptionType:** CANCELLATION, DIVERSION, DELAY, GATE_CHANGE
- **OptionType:** REBOOK, HOTEL, GROUND, ALT_AIRPORT
- **PassengerStatus:** UNAFFECTED → NOTIFIED → CHOSE → APPROVED/DENIED
- **WishStatus:** PENDING → APPROVED/DENIED

## Database

PostgreSQL 17 via docker-compose (`backend/docker-compose.yml`). Schema auto-created by SQLAlchemy on startup. Connection: `postgresql+asyncpg://softlanding:softlanding@localhost/softlanding`.

## Environment

Copy `.env.example` to `.env`. Required for external integrations: `GEMINI_API_KEY`, `LH_API_CLIENT_ID`, `LH_API_CLIENT_SECRET`. The backend runs without these using seed data and the disruption simulator.

## Issue Tracking

This project uses **bd (beads)** for all task tracking. Do NOT use markdown TODOs. See AGENTS.md for the full workflow. Key commands:

```bash
bd ready --json           # Find available work
bd update <id> --claim    # Claim a task
bd close <id>             # Complete work
```

## Session Completion Protocol

Work is NOT complete until `git push` succeeds. Before ending a session:

1. File issues for remaining work (`bd create`)
2. Run quality gates (tests, lint, build)
3. `git pull --rebase && bd sync && git push`
4. Verify `git status` shows "up to date with origin"

## Versioning

CalVer format `YYYY.0M.MICRO` in the `VERSION` file. Production at https://softlanding.sussdorff.de. CI/CD via GitHub Actions deploys on push to main.
