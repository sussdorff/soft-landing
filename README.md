# Soft Landing

> Airline disruption management — a gate agent handles 200+ stranded passengers in minutes, not hours.

Soft Landing automatically generates rebooking, hotel, and transport options when flights are cancelled, delayed, or diverted. Passengers rank their preferences in real time via a companion app, and the gate agent approves or denies them from a live dashboard. Built with Python/FastAPI, React/TypeScript, PostgreSQL, WebSockets, and Gemini AI.

**[Live Demo](https://get-softlanding.sussdorff.de)** | **[Dashboard](https://softlanding.sussdorff.de/dashboard/)** | **[API Docs](https://softlanding.sussdorff.de/api/docs)**

---

## How It Works

```
Disruption detected (cancellation, delay, diversion)
       │
       ▼
System generates options per passenger (rebook, hotel, ground transport)
       │
       ▼
Passenger picks preference via app (= wish/hint, not a booking)
       │
       ▼
Wish appears on Gate Agent Dashboard (priority-sorted, real-time)
       │
       ├── Approved → Passenger confirmed, conflicting options auto-updated
       └── Denied   → Passenger notified, new options presented, priority bumped
```

Passengers are differentiated by loyalty tier (HON Circle, Senator, Frequent Traveller) and booking class — affecting hotel quality, transport mode, lounge access, and rebooking scope.

---

## Architecture

| Component | Tech | Description |
|-----------|------|-------------|
| **Backend** | Python 3.14, FastAPI, async SQLAlchemy, PostgreSQL | Disruption engine, option generation, state management, WebSocket push |
| **Dashboard** | React 19, TypeScript, Vite, Tailwind CSS 4 | Gate agent command center — Flight Overview, Wish Stream, Resolved view |
| **Passenger App** | Kotlin Multiplatform | Disruption notifications, option selection, real-time status updates |

### External Integrations

| Service | Purpose |
|---------|---------|
| **Lufthansa API** | Flight schedules, seat availability, lounge data |
| **Gemini + Google Search** | Hotels, ground transport, weather context, plain-language disruption explanations |
| **Google Maps** | Transport routing, hotel proximity |

### Data Flow

Disruption event → DisruptionEngine classifies → finds affected passengers → OptionGenerator creates alternatives → stored in PostgreSQL → WebSocket pushes to dashboard and passenger app. Passengers submit wishes (ranked preferences) → gate agent approves/denies → WebSocket notifies passenger.

---

## Getting Started

### Prerequisites

- Python 3.14 (via [uv](https://docs.astral.sh/uv/))
- Node.js 22+
- Docker (for PostgreSQL)

### Backend

```bash
cd backend
docker compose up -d                      # Start PostgreSQL
uv sync --python python3.14               # Install dependencies
cp .env.example .env                      # Configure API keys (optional)
uvicorn app.main:app --reload             # Dev server on :8000
```

The backend auto-seeds a snowstorm scenario on startup. External API keys (`GEMINI_API_KEY`, `LH_API_CLIENT_ID`, `LH_API_CLIENT_SECRET`) are optional — the system works with seed data and the built-in disruption simulator.

### Dashboard

```bash
cd dashboard
npm install
npm run dev                               # Dev server with HMR
```

### Run Tests

```bash
cd backend
uv run pytest                             # All tests
uv run pytest -k "test_name"              # Single test
```

---

## Demo Scenarios

### Snowstorm in Munich (Hub Disruption)
8 flights cancelled, 150+ connecting passengers. Each gets personalized options based on loyalty tier and booking class. Gate agent resolves all from the dashboard.

### Aircraft Malfunction (Diversion)
Mid-flight diversion to nearest airport. 30 passengers get reroute, hotel, and ground transport options while still airborne.

---

## Deployment

Hosted on Hetzner (ARM, cax11). Caddy handles TLS and routing.

```bash
bash infra/deploy.sh all          # Deploy everything
bash infra/deploy.sh backend      # Backend only
bash infra/deploy.sh dashboard    # Dashboard only
```

| URL | What |
|-----|------|
| [get-softlanding.sussdorff.de](https://get-softlanding.sussdorff.de) | Landing page |
| [softlanding.sussdorff.de/dashboard/](https://softlanding.sussdorff.de/dashboard/) | Gate Agent Dashboard |
| [softlanding.sussdorff.de/api/docs](https://softlanding.sussdorff.de/api/docs) | Swagger API explorer |
| [softlanding.sussdorff.de/api/redoc](https://softlanding.sussdorff.de/api/redoc) | API reference |

---

## Project Structure

```
soft-landing/
├── backend/          Python FastAPI backend
│   ├── app/
│   │   ├── main.py              Entry point
│   │   ├── models.py            Pydantic API models
│   │   ├── store.py             Async CRUD layer
│   │   ├── ws.py                WebSocket manager
│   │   ├── disruption_engine.py Event classification + option orchestration
│   │   ├── option_generator.py  Deterministic option creation
│   │   ├── gemini.py            Gemini AI integration
│   │   ├── lufthansa.py         LH API client with OAuth2
│   │   ├── db/                  SQLAlchemy engine + ORM models
│   │   └── seeds/               Demo scenarios
│   └── tests/
├── dashboard/        React gate agent dashboard
│   └── src/
│       ├── api/                 Backend adapter layer
│       ├── hooks/               Data fetching hooks
│       └── types/               TypeScript type definitions
├── passenger-app/    Kotlin Multiplatform (Android, iOS, Web)
├── infra/            Deployment scripts + Caddyfile
├── deck/             Presentation slides (Slidev)
└── docs/             User documentation (MkDocs)
```

---

## Team

Jorg (mobile app) · David (dashboard) · Malte (backend & infra) · Claude & Gemini
