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
        PAX["Passenger App<br/>(Kotlin Multiplatform)"]
        DASH["Gate Agent Dashboard<br/>(React)"]
    end

    LH_OPS -->|MQTT events| DE
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
        SM_CASCADE["Cascade Engine"]
    end

    DE_NOTIFY --> OG
    OG --> SM
```

---

## Data Flow — End-to-End Workflow

```mermaid
sequenceDiagram
    participant LH as Lufthansa API
    participant DE as Disruption Engine
    participant OG as Option Generator
    participant SM as State Manager
    participant PAX as Passenger App
    participant GA as Gate Agent Dashboard

    LH->>DE: MQTT disruption event<br/>(cancellation/diversion/delay)
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
    SM->>PAX: Push notification + options
    PAX->>PAX: Passenger views explanation + options
    PAX->>SM: Submit preference (wish)
    SM->>GA: Wish appears in real-time stream

    alt Gate Agent Approves
        GA->>SM: Approve wish
        SM->>PAX: Confirmation + next steps
    else Gate Agent Denies
        GA->>SM: Deny wish (with reason)
        SM->>SM: Bump passenger priority
        SM->>OG: Regenerate options (exclude denied)
        OG->>SM: Updated options
        SM->>PAX: New options presented
    end
```

---

## Component Details & Implementable Modules

### Module 1: Disruption Engine

```mermaid
graph TD
    subgraph Input
        MQTT["MQTT Listener<br/>LH Flight Ops API"]
    end

    subgraph Processing
        PARSE["Event Parser<br/>─────────────<br/>• Cancellation<br/>• Diversion<br/>• Delay"]
        SCOPE["Impact Calculator<br/>─────────────<br/>• Find affected flights<br/>• Find affected passengers<br/>• Check connections"]
        ENRICH["Context Enricher<br/>─────────────<br/>• Weather (Google Search)<br/>• NOTAM status<br/>• Airport conditions"]
    end

    subgraph Output
        TRIGGER["Trigger Option<br/>Generation per<br/>affected passenger"]
    end

    MQTT --> PARSE --> SCOPE --> ENRICH --> TRIGGER

    style MQTT fill:#ffd8a8
    style TRIGGER fill:#b2f2bb
```

**Deliverables:**
- MQTT client subscribing to LH Flight Ops events
- Event parser supporting cancellation, diversion, delay types
- Affected passenger lookup (connecting passengers, destination passengers)
- Context enrichment via Gemini + Google Search grounding

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
        CASCADE["Cascade Engine<br/>─────────────<br/>• Seat conflict detection<br/>• Impact preview<br/>• Option invalidation"]
        APPROVE["Approval Handler<br/>─────────────<br/>• Lock resources<br/>• Confirm to passenger<br/>• Update dashboard"]
        DENY["Denial Handler<br/>─────────────<br/>• Bump priority<br/>• Trigger re-generation<br/>• Notify passenger"]
    end

    PAX_REG --> CASCADE
    WISH --> CASCADE
    PRIO --> CASCADE
    CASCADE --> APPROVE
    CASCADE --> DENY

    style CASCADE fill:#ffc9c9
    style APPROVE fill:#b2f2bb
    style DENY fill:#ffc9c9
```

**Deliverables:**
- Passenger state store (in-memory for hackathon, with clear interfaces)
- Wish tracking with ranked preference support
- Priority queue with denial-based escalation
- Cascade engine: when approving one wish, detect conflicts with other passengers' wishes
- Approval/denial handlers with real-time notification dispatch

---

### Module 4: Passenger App (Kotlin Multiplatform)

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

### Module 5: Gate Agent Dashboard (React)

```mermaid
graph TD
    subgraph Views["Dashboard Views"]
        V1["Overview Panel<br/>─────────────<br/>• All affected passengers<br/>• At-a-glance stats<br/>• % connection risk"]
        V2["Wish Stream<br/>─────────────<br/>• Real-time feed<br/>• Sorted by priority<br/>• Denial count badges"]
        V3["Approval Panel<br/>─────────────<br/>• One-click approve<br/>• Cascade impact preview<br/>• Deny with reason"]
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
- Approval workflow with cascading impact preview
- Manual resolution view for edge cases

---

## Implementation Priority

```mermaid
gantt
    title Implementation Roadmap
    dateFormat X
    axisFormat %s

    section Phase 1 — Core
    Backend scaffolding + API          :p1, 0, 2
    State Manager (in-memory)          :p2, 0, 2
    Mock disruption data               :p3, 0, 1

    section Phase 2 — Options
    Flight rebook module               :p4, 2, 4
    Hotel + next-day module            :p5, 2, 4
    Ground transport module            :p6, 2, 4
    Gemini explanation generator       :p7, 2, 4

    section Phase 3 — Interfaces
    Passenger App (KMP) screens        :p8, 4, 7
    Gate Agent Dashboard (React)       :p9, 4, 7
    WebSocket real-time layer          :p10, 4, 6

    section Phase 4 — Logic
    Priority queue + escalation        :p11, 6, 8
    Cascade engine                     :p12, 6, 8
    Approval/denial flow               :p13, 7, 9

    section Phase 5 — Integration
    MQTT disruption listener           :p14, 8, 9
    End-to-end demo scenarios          :p15, 9, 10
```

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
