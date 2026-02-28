# Soft Landing — Software Architecture

> Decomposition of the system into implementable components

---

## High-Level System Overview

```mermaid
graph TB
    subgraph External["External Services"]
        LH_OPS["Lufthansa Flight Ops API<br/>(MQTT Push)"]
        LH_SCHED["Lufthansa Schedules API"]
        LH_SEATS["Lufthansa Seat Maps API"]
        LH_REF["Lufthansa Reference Data API"]
        GEMINI["Google Gemini 3.0<br/>(with Grounding)"]
        GMAPS["Google Maps API"]
        GSEARCH["Google Search"]
    end

    subgraph Backend["Backend / Agent Server (Python 3.14)"]
        DE["Disruption Engine"]
        OG["Option Generator"]
        SM["State Manager"]
        WS_SERVER["WebSocket Server"]
        API["REST API"]
    end

    subgraph Clients["Client Applications"]
        DASH["Gate Agent Dashboard<br/>(React) — Primary Product"]
        PAX["Passenger App<br/>(Kotlin Multiplatform)"]
    end

    LH_OPS -.->|MQTT events - later| DE
    DE -->|disruption context| OG
    LH_SCHED --> OG
    LH_SEATS --> OG
    LH_REF --> OG
    GEMINI --> OG
    GMAPS --> OG
    GSEARCH --> OG
    OG -->|options per passenger| SM
    SM <-->|real-time updates| WS_SERVER
    SM <-->|request/response| API
    WS_SERVER <-->|live stream| DASH
    API <-->|options & wishes| PAX
    WS_SERVER <-->|notifications| PAX
```

---

## Component Decomposition

```mermaid
graph LR
    subgraph DE["1. Disruption Engine"]
        DE_MQTT["MQTT Listener"]
        DE_PARSE["Event Parser"]
        DE_SCOPE["Impact Scope<br/>Calculator"]
        DE_NOTIFY["Notification<br/>Dispatcher"]
    end

    DE_MQTT --> DE_PARSE --> DE_SCOPE --> DE_NOTIFY

    subgraph OG["2. Option Generator"]
        OG_FLIGHT["Flight Rebooking<br/>Module"]
        OG_HOTEL["Hotel + Next-Day<br/>Module"]
        OG_GROUND["Ground Transport<br/>Module"]
        OG_ALT["Alt. Airport<br/>Module"]
        OG_EXPLAIN["Explanation<br/>Generator (Gemini)"]
    end

    subgraph SM["3. State Manager"]
        SM_PAX["Passenger Registry"]
        SM_WISH["Wish Tracker"]
        SM_PRIO["Priority Queue"]
        SM_CONFLICT["Conflict Notifier"]
    end

    DE_NOTIFY --> OG
    OG --> SM
```

---

## Data Flow — End-to-End Workflow

```mermaid
sequenceDiagram
    participant SIM as Disruption Simulator
    participant DE as Disruption Engine
    participant OG as Option Generator
    participant SM as State Manager
    participant PAX as Passenger App
    participant GA as Gate Agent Dashboard

    SIM->>DE: Inject mock disruption<br/>(POST /disruptions/simulate)
    Note over SIM,DE: MQTT listener can replace<br/>simulator in production

    DE->>DE: Parse event, identify affected passengers
    DE->>OG: Generate options for each passenger

    par Option Generation
        OG->>OG: Query flights (LH Schedules)
        OG->>OG: Query seats (LH Seat Maps)
        OG->>OG: Query ground transport (Google Maps)
        OG->>OG: Query hotels (Google Maps)
        OG->>OG: Generate explanation (Gemini + Search)
    end

    OG->>SM: Store options per passenger
    SM->>GA: disruption_created (WebSocket)
    SM->>PAX: options_available (WebSocket)
    PAX->>PAX: Passenger views explanation + options
    PAX->>SM: Submit preference (POST /passengers/:id/wish)
    SM->>GA: new_wish (WebSocket, real-time stream)

    alt Gate Agent Approves
        GA->>SM: POST /wishes/:id/approve
        SM->>PAX: wish_confirmed (WebSocket)
        SM->>SM: Mark conflicting options unavailable
        SM->>PAX: options_updated (to affected passengers)
    else Gate Agent Denies
        GA->>SM: POST /wishes/:id/deny
        SM->>SM: Bump passenger priority
        SM->>OG: Regenerate options (exclude denied)
        OG->>SM: Updated options
        SM->>PAX: wish_rejected + new options (WebSocket)
    end
```

---

## Component Details & Implementable Modules

### Module 1: Disruption Engine

```mermaid
graph TD
    subgraph Input
        SIM["Disruption Simulator<br/>─────────────<br/>CLI / API endpoint<br/>Inject mock events"]
        MQTT["MQTT Listener<br/>LH Flight Ops API<br/>(wire up last)"]
    end

    subgraph Processing
        PARSE["Event Parser<br/>─────────────<br/>• Cancellation<br/>• Diversion<br/>• Delay"]
        SCOPE["Impact Calculator<br/>─────────────<br/>• Find affected flights<br/>• Find affected passengers<br/>• Check connections"]
        ENRICH["Context Enricher<br/>─────────────<br/>• Weather (Google Search)<br/>• NOTAM status<br/>• Airport conditions"]
    end

    subgraph Output
        TRIGGER["Trigger Option<br/>Generation per<br/>affected passenger"]
    end

    SIM --> PARSE
    MQTT -.->|later| PARSE
    PARSE --> SCOPE --> ENRICH --> TRIGGER

    style SIM fill:#b2f2bb
    style MQTT fill:#ffd8a8
    style TRIGGER fill:#b2f2bb
```

**Deliverables:**
- **Disruption simulator** (Phase 1, day one): CLI command or REST endpoint that injects mock disruption events directly into the engine — enables full-pipeline testing without MQTT
- Event parser supporting cancellation, diversion, delay types
- Affected passenger lookup (connecting passengers, destination passengers)
- Context enrichment via Gemini + Google Search grounding
- MQTT client subscribing to LH Flight Ops events (Phase 4, if time allows)

---

### Module 2: Option Generator

```mermaid
graph TD
    subgraph Strategies["Resolution Strategies"]
        S1["Flight Rebook<br/>─────────────<br/>• Query LH Schedules<br/>• Check seat availability<br/>• Same day / next day"]
        S2["Hotel + Next Day<br/>─────────────<br/>• Nearby hotels (Maps)<br/>• Next morning flights<br/>• Transfer logistics"]
        S3["Ground Transport<br/>─────────────<br/>• Train routes (Maps)<br/>• Bus alternatives<br/>• Drive time estimates"]
        S4["Alt. Airport Route<br/>─────────────<br/>• Nearby airports (LH Ref)<br/>• Connecting flights<br/>• Total journey time"]
    end

    subgraph Presentation
        RANK["Option Ranker<br/>─────────────<br/>• Fastest arrival<br/>• Least disruption<br/>• Cost efficiency"]
        EXPLAIN["Gemini Explainer<br/>─────────────<br/>• Plain-language why<br/>• Option descriptions<br/>• Grounded in facts"]
    end

    S1 --> RANK
    S2 --> RANK
    S3 --> RANK
    S4 --> RANK
    RANK --> EXPLAIN

    style RANK fill:#d0bfff
    style EXPLAIN fill:#d0bfff
```

**Deliverables:**
- 4 strategy modules (flight, hotel, ground, alt-airport), each callable independently
- Option ranking by arrival time and disruption level
- Gemini-powered plain-language explanations with Google Search/Maps grounding
- Returns 3-4 concrete options per passenger

---

### Module 3: State Manager

```mermaid
graph TD
    subgraph Core["Core State"]
        PAX_REG["Passenger Registry<br/>─────────────<br/>• Original itinerary<br/>• Current status<br/>• Denial count"]
        WISH["Wish Tracker<br/>─────────────<br/>• Selected option<br/>• Ranked preferences<br/>• Timestamps"]
        PRIO["Priority Queue<br/>─────────────<br/>• Default: timestamp order<br/>• +1 denial: above first-choice<br/>• +2 denials: highest priority"]
    end

    subgraph Logic["Business Logic"]
        APPROVE["Approval Handler<br/>─────────────<br/>• Mark option taken<br/>• Confirm to passenger<br/>• Update dashboard"]
        CONFLICT["Conflict Notifier<br/>─────────────<br/>• Post-approval check<br/>• Mark conflicting options<br/>  as unavailable<br/>• Notify affected passengers"]
        DENY["Denial Handler<br/>─────────────<br/>• Bump priority<br/>• Trigger re-generation<br/>• Notify passenger"]
    end

    PAX_REG --> APPROVE
    WISH --> APPROVE
    PRIO --> APPROVE
    APPROVE --> CONFLICT
    CONFLICT --> DENY

    style CONFLICT fill:#fff3bf
    style APPROVE fill:#b2f2bb
    style DENY fill:#ffc9c9
```

**Deliverables:**
- Passenger state store (in-memory for hackathon, with clear interfaces)
- Wish tracking with ranked preference support
- Priority queue with denial-based escalation
- **Simplified conflict handling:** when a wish is approved, mark conflicting options as unavailable and notify affected passengers (no pre-approval impact preview — keep it simple)
- Approval/denial handlers with real-time notification dispatch

---

### Module 4: Gate Agent Dashboard (React) — Primary Product

```mermaid
graph TD
    subgraph Views["Dashboard Views"]
        V1["Overview Panel<br/>─────────────<br/>• All affected passengers<br/>• At-a-glance stats<br/>• % connection risk"]
        V2["Wish Stream<br/>─────────────<br/>• Real-time feed<br/>• Sorted by priority<br/>• Denial count badges"]
        V3["Approval Panel<br/>─────────────<br/>• One-click approve<br/>• Deny with reason<br/>• Conflicts auto-resolved"]
        V4["Manual Resolution<br/>─────────────<br/>• Passenger profile<br/>• Full history<br/>• Override tools"]
    end

    WS["WebSocket Connection<br/>to Backend"]

    WS <--> V1
    WS <--> V2
    WS <--> V3
    WS <--> V4

    style WS fill:#ffd8a8
```

**Deliverables:**
- React SPA with WebSocket connection for real-time updates
- Overview panel with disruption stats
- Live wish stream sorted by priority (denied passengers first)
- Approval workflow with post-approval conflict notification
- Manual resolution view for edge cases

---

### Module 5: Passenger App (Kotlin Multiplatform)

```mermaid
graph TD
    subgraph Screens["App Screens"]
        S1["Disruption Alert<br/>─────────────<br/>• What happened<br/>• Why (plain language)<br/>• What it means for you"]
        S2["Options View<br/>─────────────<br/>• Default rebook (if any)<br/>• 3-4 alternatives<br/>• Details per option"]
        S3["Preference Selector<br/>─────────────<br/>• Single choice<br/>• Or ranked preferences<br/>• Submit as wish"]
        S4["Status Tracker<br/>─────────────<br/>• Waiting for approval<br/>• Approved + next steps<br/>• Denied + new options"]
    end

    S1 --> S2 --> S3 --> S4
    S4 -.->|denied| S2

    style S1 fill:#ffc9c9
    style S2 fill:#a5d8ff
    style S3 fill:#d0bfff
    style S4 fill:#b2f2bb
```

**Deliverables:**
- Compose Multiplatform UI (Android, iOS, Web targets)
- Push notification receiver (WebSocket-based)
- API client for backend communication
- 4 main screens: alert, options, preference selector, status tracker

---

## Implementation Priority

All three components (backend, passenger app, dashboard) are built **in parallel from day one**. The backend starts with hardcoded mock responses so frontends can develop against real API shapes immediately. Real API integrations are swapped in later.

```mermaid
gantt
    title Implementation Roadmap (Parallel)
    dateFormat X
    axisFormat %s

    section Phase 1 — Foundation (all teams)
    API contract + shared types        :p1, 0, 1
    Disruption simulator (mock trigger):p2, 0, 1
    Backend scaffolding + mock API     :p3, 0, 2
    State Manager (in-memory)          :p4, 0, 2
    Passenger App scaffold + screens   :p5, 0, 2
    Gate Agent Dashboard scaffold      :p6, 0, 2

    section Phase 2 — Core Features (parallel)
    Flight rebook module               :p7, 2, 4
    Hotel + next-day module            :p8, 2, 4
    Ground transport module            :p9, 2, 4
    Gemini explanation generator       :p10, 2, 4
    Dashboard wish stream + approve    :p11, 2, 4
    Passenger App options + wish flow  :p12, 2, 4
    WebSocket real-time layer          :p13, 2, 4

    section Phase 3 — Logic + Polish
    Priority queue + escalation        :p14, 4, 6
    Post-approval conflict notify      :p15, 4, 6
    Approval/denial flow end-to-end    :p16, 4, 6

    section Phase 4 — Integration + Demo
    Swap mocks for real LH/Gemini APIs :p17, 6, 8
    MQTT listener (if time allows)     :p18, 7, 8
    End-to-end demo scenarios          :p19, 8, 10
```

---

## API Contract (Phase 1 — define before building)

The shared data model that all three components agree on. Defined upfront so backend and frontends can be built in parallel against the same shapes.

### Core Types

```mermaid
classDiagram
    class Disruption {
        +string id
        +string type: cancellation | diversion | delay
        +string flightNumber
        +string origin
        +string destination
        +string reason
        +string explanation (Gemini plain-language)
        +datetime detectedAt
        +string[] affectedPassengerIds
    }

    class Passenger {
        +string id
        +string name
        +string bookingRef
        +Itinerary originalItinerary
        +string status: unaffected | notified | chose | approved | denied
        +int denialCount
        +int priority
    }

    class Itinerary {
        +Segment[] segments
    }

    class Segment {
        +string flightNumber
        +string origin
        +string destination
        +datetime departure
        +datetime arrival
    }

    class Option {
        +string id
        +string type: rebook | hotel | ground | alt_airport
        +string summary
        +string description
        +object details
        +bool available
        +datetime estimatedArrival
    }

    class RebookDetails {
        +string flightNumber
        +string origin
        +string destination
        +datetime departure
        +string seatAvailable
    }

    class HotelDetails {
        +string hotelName
        +string address
        +LatLng location
        +string nextFlightNumber
        +datetime nextFlightDeparture
    }

    class GroundTransportDetails {
        +string mode: train | bus
        +string route
        +datetime departure
        +datetime arrival
        +string provider
    }

    class AltAirportDetails {
        +string viaAirport
        +string connectingFlight
        +string transferMode: train | bus | taxi
        +datetime totalArrival
    }

    Option --> RebookDetails
    Option --> HotelDetails
    Option --> GroundTransportDetails
    Option --> AltAirportDetails

    class Wish {
        +string id
        +string passengerId
        +string disruptionId
        +string selectedOptionId
        +string[] rankedOptionIds
        +datetime submittedAt
        +string status: pending | approved | denied
        +string denialReason
        +string confirmationDetails
    }

    Passenger --> Itinerary
    Itinerary --> Segment
    Disruption --> Passenger
    Passenger --> Wish
    Wish --> Option
```

### WebSocket Event Types

```mermaid
graph LR
    subgraph Server to Dashboard
        E1["new_wish<br/>─────────────<br/>Passenger submitted<br/>a preference"]
        E2["wish_approved<br/>─────────────<br/>Gate agent approved,<br/>conflicts resolved"]
        E3["wish_denied<br/>─────────────<br/>Option no longer<br/>available"]
        E4["disruption_created<br/>─────────────<br/>New disruption event<br/>with affected passengers"]
    end

    subgraph Server to Passenger App
        E5["options_available<br/>─────────────<br/>Your options are ready"]
        E6["wish_confirmed<br/>─────────────<br/>Approved + next steps"]
        E7["wish_rejected<br/>─────────────<br/>Denied + new options"]
        E8["options_updated<br/>─────────────<br/>Some options changed<br/>availability"]
    end
```

### WebSocket Connections

```
WS /ws/passenger/{passenger_id}     ← Passenger App connects here
WS /ws/dashboard/{disruption_id}    ← Gate Agent Dashboard connects here
```

**Message envelope** (all WS messages use this shape):

```json
{
  "type": "wish_confirmed | options_available | ...",
  "timestamp": "2026-03-01T14:30:00Z",
  "data": { ... }
}
```

### REST Endpoints

| Method | Path | Used by | Purpose |
|--------|------|---------|---------|
| POST | `/disruptions/simulate` | Simulator | Inject mock disruption |
| GET | `/disruptions/:id` | Dashboard | Get disruption details + explanation |
| GET | `/disruptions/:id/passengers` | Dashboard | List affected passengers (sorted by priority → timestamp) |
| GET | `/passengers/:id/disruptions` | Passenger App | List active disruptions affecting this passenger |
| GET | `/passengers/:id/options` | Passenger App | Get available options with details |
| GET | `/passengers/:id/status` | Passenger App | Current state: waiting / approved / denied |
| POST | `/passengers/:id/wish` | Passenger App | Submit ranked preference(s) |
| GET | `/passengers/:id/profile` | Dashboard | Full profile for manual resolution (itinerary, wishes, denial history) |
| POST | `/wishes/:id/approve` | Dashboard | Approve a wish |
| POST | `/wishes/:id/deny` | Dashboard | Deny a wish with reason |
| GET | `/wishes?disruption_id=X` | Dashboard | All wishes for a disruption |

**Authentication (hackathon scope):**
- Passenger App: booking reference + last name as token
- Gate Agent Dashboard: static API key or unauth'd for demo

---

## Technology Map

```mermaid
graph LR
    subgraph Languages
        PY["Python 3.14"]
        KT["Kotlin (KMP)"]
        TS["TypeScript"]
    end

    subgraph Frameworks
        FAST["FastAPI / Flask"]
        COMPOSE["Compose Multiplatform"]
        REACT["React"]
    end

    subgraph Protocols
        MQTT["MQTT"]
        WSP["WebSockets"]
        REST["REST API"]
    end

    subgraph AI
        GEM["Gemini 3.0"]
        GROUND_S["Google Search Grounding"]
        GROUND_M["Google Maps Grounding"]
    end

    PY --- FAST
    KT --- COMPOSE
    TS --- REACT

    FAST --- REST
    FAST --- WSP
    FAST --- MQTT

    COMPOSE --- REST
    COMPOSE --- WSP
    REACT --- WSP

    FAST --- GEM
    GEM --- GROUND_S
    GEM --- GROUND_M

    style PY fill:#fff3bf
    style KT fill:#d0bfff
    style TS fill:#a5d8ff
```
