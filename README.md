# Soft Landing — Passenger Disruption Management

> A single gate agent can handle 200 disrupted passengers in minutes instead of hours.

When flights break, passengers crowd the desk and gate agents drown in manual rebooking. Soft Landing gives the gate agent an **operational command center** that surfaces every affected passenger, their preferences, and the cascading impact of each decision — in real time. Passengers self-serve through a companion app, expressing preferences that stream directly into the agent's dashboard. The agent stays in control with human-in-the-loop approval, while AI handles the heavy lifting of generating options and explaining disruptions.

---

## Three Components

1. **Gate Agent Dashboard** (React, WebSocket-based) — The primary product. Operator sees all affected passengers, their wishes, approves/denies, handles conflicts. Human-in-the-loop with final say. Real-time updates as passenger wishes stream in.

2. **Backend / Agent Server** (Python) — The brain. Connects to Lufthansa API + Google Grounding. Detects disruptions, generates options, manages state, handles conflict resolution.

3. **Passenger App** (Kotlin Multiplatform — Android, iOS, Web) — The data collection layer. Each passenger gets notifications and options. They express preferences that feed directly into the gate agent's dashboard.

---

## Passenger App — Detailed Flow

### 1. Disruption Notification
- Passenger receives: "Your connecting flight LH1234 MUC→CDG is cancelled"
- **Plain-language explanation of WHY**: "Due to heavy snowfall in Munich, all departures are suspended until further notice. Here's what this means for you and what your options are."
- Goal: create understanding and compassion — passenger knows the situation, doesn't need to ask the gate agent

### 2. Default Rebooking (if exists)
- Airlines already auto-rebook passengers when disruptions happen
- App shows: "The airline has already rebooked you onto LH1238 departing tomorrow at 07:15. You're covered."
- But also: "If you'd prefer a different option, here are alternatives:"
- The default is already locked in — passenger only needs to act if they want something different

### 3. Options (when no default, or passenger wants change)
- 3-4 concrete options with details:
  - **Rebook**: "LH1238 MUC→CDG departing 18:45, seat 14A available" (Seat Maps API)
  - **Hotel + next day**: "Hilton Munich Airport, flight tomorrow 07:15" (Google Maps)
  - **Ground transport**: "ICE train MUC→Paris, departs 16:30, arrives 22:15" (Google Maps)
  - **Alternative airport**: "Fly to FRA, then train to Paris" (Schedules + Maps)
- Passenger selects preference (or ranked preferences for better cascading resolution)

### 4. Preference = Hint, Not Booking
- Passenger's choice is a **wish / hint** sent to the gate agent
- NOT automatically locked in
- Gate agent must approve
- On approval → passenger gets: "Your choice has been approved. Here's what happens next: [clear next steps]"

### 5. Denial Flow
- If gate agent denies (or cascading impact makes choice impossible):
  - Passenger is informed: "Unfortunately, your preferred option is no longer available because [reason]"
  - New options presented
  - Passenger chooses again

### 6. Priority Escalation
- Passengers denied once or twice get **bumped up in the dashboard queue**
- Default sort: by timestamp (first come, first served)
- After 1 denial: ranked above all first-choice passengers
- After 2 denials: highest priority — gate agent sees these first
- Goal: avoid a passenger getting denied 3, 4, 5 times

---

## Gate Agent Dashboard — Detailed Flow

### 1. At-a-Glance Overview
- All passengers affected by disruption
- Highlighted: "80% of passengers on flight LH456 will miss their connection"
- Can instruct passengers at gate: "Please open the Soft Landing app for your rebooking options"

### 2. Passenger Wishes Stream In
- Real-time list of passengers and their chosen preferences
- Sorted by: priority (denied passengers first) → timestamp
- Each entry shows: passenger name, original itinerary, chosen option, denial count

### 3. Approve / Deny
- One-click approve
- On approve: conflicting options for other passengers are automatically marked unavailable and those passengers are notified with updated options
- Gate agent has **final say** on everything
- Deny with reason → passenger gets notified with new options

### 4. Manual Resolution
- For edge cases the AI can't resolve
- Passenger comes to desk → agent already sees their profile, wishes, history
- No digging through individual records — everything prepared

---

## Demo Scenarios

### Scenario 1: Aircraft Malfunction → Diversion
- Real existing flight
- Simulate: aircraft malfunction, must divert to nearest airport
- Passengers on board get options mid-flight via app
- Demo: passenger choosing between reroute / hotel / ground transport

### Scenario 2: Snowstorm in Munich → Hub Disruption
- No flights leaving Munich
- Different handling by passenger type:
  - **Destination = Munich** → "You're fine, welcome to Munich" (no action needed)
  - **Connecting through Munich** → Full option set:
    - Connecting flights still departing? Rebook
    - Reroute via Frankfurt or another hub?
    - Hotel overnight + morning flight?
    - Ground transport (train/bus) to final destination?

### Stretch Goal: Passenger-Triggered Incident
- Passenger: "I overslept, I'll miss my flight"
- System treats as self-reported disruption for that individual
- Lower priority — nice to have if time allows

---

## Scope Decisions

### In Scope
- Three resolution types:
  1. **Another airplane** — rebook to different flight (with seat availability)
  2. **Hotel** — stay overnight, fly next day
  3. **Ground transportation** — bus/train to final destination
- Disruption explanation to passengers (plain language, why it happened)
- Passenger preference/wish submission (ranked choices)
- Gate agent approval workflow with cascading impact visibility
- Priority escalation for denied passengers
- Confirmation flow (approved → "here's what happens next")

### Explicitly Out of Scope
- Luggage and cargo handling
- Behind-the-scenes operations (crew, maintenance, aircraft swap)
- Actual booking system integration (we simulate/mock)
- Payment processing
- EU261 compensation handling
- Option reservation / seat holding (too complex for hackathon)

---

## API + Grounding Usage

| Feature | API/Tool | How |
|---------|----------|-----|
| Detect disruption | LH Flight Ops API (MQTT push) | Cancellation, diversion, delay events |
| Find alternative flights | LH Schedules API | Search routes from current/nearby airports |
| Check seat availability | LH Seat Maps API | Show available seats on alternatives |
| Ground transport options | Gemini + Google Maps | Public transit, bus, train routes + times |
| Hotel recommendations | Gemini + Google Maps | Nearby hotels with availability |
| Disruption context/explanation | Gemini + Google Search | Weather, NOTAM, airport status → plain language |
| Nearest airports | LH Reference Data API | Airport coordinates + distances |

---

## Architecture

```
                    ┌─────────────────────────┐
                    │    Backend / Agent       │
                    │                         │
                    │  ┌───────────────────┐  │
  Disruption ──────►│  │ Disruption Engine │  │
  Simulator         │  └────────┬──────────┘  │
  (MQTT later)      │           │              │
                    │  ┌────────▼──────────┐  │
                    │  │ Option Generator  │  │
                    │  │                   │  │
  LH Schedules ───►│  │  Flights / Seats  │  │
  LH Seat Maps ───►│  │  Hotels / Transit │  │
  Google Maps ─────►│  │                   │  │
  Google Search ───►│  └────────┬──────────┘  │
                    │           │              │
                    │  ┌────────▼──────────┐  │
                    │  │  State Manager    │  │
                    │  │  (wishes, status, │  │
                    │  │   priorities,     │  │
                    │  │   conflicts)      │  │
                    │  └──┬────────────┬───┘  │
                    └─────┼────────────┼──────┘
                          │            │
              ┌───────────▼──────────┐ │
              │ Gate Agent Dashboard │ │  ◄── PRIMARY PRODUCT
              │ (React + WebSocket)  │ │
              │                      │ │
              │ - All pax at         │ │
              │   a glance           │ │
              │ - Wishes stream      │ │
              │ - Approve/deny       │ │
              │ - Priority queue     │ │
              │   (denied pax        │ │
              │    bumped up)        │ │
              └──────────────────────┘ │
                               ┌───────▼──────────┐
                               │ Passenger App    │
                               │ (KMP)            │
                               │                  │
                               │ - Why it happened│
                               │ - Your options   │
                               │ - Pick preference│
                               │ - Status updates │
                               └──────────────────┘
```

---

## Workflow Summary

```
Disruption detected
       │
       ▼
System generates options per passenger
       │
       ├── Has auto-rebook default? → Show default + alternatives
       │
       └── No default? → Show options, ask for choice (or ranked choices)
              │
              ▼
       Passenger picks preference (= hint)
              │
              ▼
       Wish appears on Gate Agent Dashboard
       (sorted: denied pax first, then by timestamp)
              │
              ▼
       Gate Agent approves or denies
              │
       ┌──────┴──────┐
       ▼              ▼
   Approved        Denied
       │              │
       ▼              ▼
   "Confirmed!     "Sorry, no longer
    Here's what     available. Here
    happens next"   are new options"
                      │
                      ▼
                   Passenger bumped
                   up in priority,
                   chooses again
```

---

## Open Questions

- [x] ~~App implementation for demo~~ → Kotlin Multiplatform (Android, iOS, Web)
- [x] ~~Frontend framework choice~~ → KMP with Compose Multiplatform for passenger app; React for gate agent dashboard
- [x] ~~Real-time updates~~ → WebSockets (critical for gate agent dashboard live updates)
- [x] ~~Gate Agent Dashboard framework~~ → React with WebSockets (reference: Mira project)
- [x] ~~Backend choice~~ → Python 3.14 (Gemini SDK, agent orchestration)
- [x] ~~How to simulate MQTT disruption events for demo?~~ → Disruption simulator (CLI/API endpoint) injects mock events; MQTT wired up last if time allows
- [x] ~~Mock data: how many passengers per scenario?~~ → Scenario 1 (diversion): 30 pax, Scenario 2 (hub disruption): 150 connecting pax
- [x] ~~Repo structure~~ → Monorepo: `backend/`, `passenger-app/`, `dashboard/`
- [x] ~~Backend framework~~ → FastAPI (async, native WS, Pydantic, auto OpenAPI)
- [x] ~~Passenger identification~~ → PNR + last name
- [x] ~~Backend access during dev~~ → Centralized mock server on Hetzner, frontends work against it

---

## Infrastructure

**Server:** Hetzner cax11 (ARM, 2C/4GB) — Ubuntu 24.04, Falkenstein
**URL:** https://softlanding.sussdorff.de
**SSH:** `ssh softlanding`

| Route | Target | Purpose |
|-------|--------|---------|
| `/dashboard/*` | Static files | Gate Agent Dashboard (React SPA) |
| `/app/*` | Static files | Passenger App (KMP web target) |
| `/*` (default) | Python backend (port 8000) | REST API + WebSocket |

**API Documentation:**

| URL | What |
|-----|------|
| [`/api/docs`](https://softlanding.sussdorff.de/api/docs) | Swagger UI — interactive API explorer (try endpoints live) |
| [`/api/redoc`](https://softlanding.sussdorff.de/api/redoc) | ReDoc — clean API reference for frontend devs |
| [`/api/openapi.json`](https://softlanding.sussdorff.de/api/openapi.json) | OpenAPI spec (use for code generation) |

**Stack on server:** Docker, Node.js 22, Python 3.14 (via uv), Caddy (reverse proxy + auto-TLS via Let's Encrypt). CORS enabled for mobile app access.

### Infrastructure as Code

All scripts in `infra/`:

| Script | Purpose |
|--------|---------|
| `setup-server.sh` | Create server, firewall, DNS record via hcloud |
| `provision.sh` | Install Docker, Node, Python, Caddy + write Caddyfile |
| `deploy.sh [all\|backend\|dashboard\|app]` | Deploy code to server |
| `teardown.sh` | Destroy server, firewall, DNS (with confirmation) |
