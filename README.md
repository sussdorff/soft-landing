# ReRoute — Passenger Disruption Management

> 2026-02-28 — Dual-view system: passenger app + gate agent dashboard + backend agent

---

## Three Components

1. **Backend / Agent Server** — The brain. Connects to Lufthansa API + Google Grounding. Detects disruptions, generates options, manages state, handles cascading logic.

2. **Passenger App** (web-based) — Each passenger gets notifications and options. They express preferences. They get informed about what's happening and why.

3. **Gate Agent Dashboard** (web-based) — Operator sees all affected passengers, their wishes, approves/denies, handles conflicts. Human-in-the-loop with final say.

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
- Can instruct passengers at gate: "Please open the ReRoute app for your rebooking options"

### 2. Passenger Wishes Stream In
- Real-time list of passengers and their chosen preferences
- Sorted by: priority (denied passengers first) → timestamp
- Each entry shows: passenger name, original itinerary, chosen option, denial count

### 3. Approve / Deny
- One-click approve
- On approve: **cascading impact shown** — "Approving seat 14A for Passenger X means Passenger Y's first choice can no longer be fulfilled"
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
  LH Flight Ops ──►│  │ Disruption Engine │  │
  API (MQTT)        │  └────────┬──────────┘  │
                    │           │              │
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
                    │  │   cascading)      │  │
                    │  └──┬────────────┬───┘  │
                    └─────┼────────────┼──────┘
                          │            │
              ┌───────────▼──┐   ┌─────▼───────────┐
              │ Passenger    │   │ Gate Agent       │
              │ App (Web)    │   │ Dashboard (Web)  │
              │              │   │                  │
              │ - Why it     │   │ - All pax at     │
              │   happened   │   │   a glance       │
              │ - Your       │   │ - Wishes stream  │
              │   options    │   │ - Approve/deny   │
              │ - Pick       │   │ - Cascading      │
              │   preference │   │   impact view    │
              │ - Status     │   │ - Priority queue │
              │   updates    │   │   (denied pax    │
              │              │   │    bumped up)    │
              └──────────────┘   └─────────────────┘
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

- [ ] App implementation for demo: responsive web page is simplest
- [ ] How to simulate MQTT disruption events for demo?
- [ ] Mock data: how many passengers per scenario?
- [ ] Frontend framework choice
- [ ] Real-time updates: WebSocket between backend and frontends?
