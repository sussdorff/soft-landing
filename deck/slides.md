---
theme: default
title: Soft Landing — Architecture
author: Soft Landing Team
colorSchema: light
aspectRatio: 16/9
canvasWidth: 980
transition: slide-left
fonts:
  sans: Inter
  mono: Fira Code
  provider: google
mdc: true
---

# Soft Landing

### Passenger Disruption Management — Software Architecture

<br>

Dual-view system: **passenger app** (KMP) + **gate agent dashboard** (React) + **backend agent** (Python)

<br>

<div style="opacity:0.5; font-size:0.9em">
Disruption Engine · Option Generator · State Manager
</div>

<!--
Cover slide. Introduce the project and the three main backend components.
-->

---
layout: section
---

# High-Level System Overview

---

# System Architecture

```mermaid {scale: 0.55}
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

    LH_OPS -.->|MQTT events| DE
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

<!--
Three layers: external services, backend agent server, client applications.
The backend orchestrates everything through Disruption Engine → Option Generator → State Manager.
-->

---
layout: section
---

# Component Decomposition

---

# Backend Components

```mermaid {scale: 0.65}
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

<!--
Three core backend modules connected in a pipeline.
Disruption Engine detects and parses events, Option Generator creates resolution options, State Manager tracks passenger choices and agent approvals.
-->

---

# Disruption Engine

<div class="grid grid-cols-2 gap-8">
<div>

```mermaid {scale: 0.55}
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
```

</div>
<div>

### Deliverables

<v-clicks>

- **Disruption simulator** — day one, mock trigger via CLI/REST
- Event parser for cancellation, diversion, delay
- Affected passenger lookup (connections, destinations)
- Context enrichment via Gemini + Google Search
- MQTT client for LH Flight Ops (Phase 4, if time)

</v-clicks>

</div>
</div>

<!--
The simulator is the key enabler — lets us develop the full pipeline without waiting for real MQTT events.
-->

---

# Option Generator

<div class="grid grid-cols-2 gap-8">
<div>

```mermaid {scale: 0.6}
graph TD
    subgraph Strategies["Resolution Strategies"]
        S1["Flight Rebook<br/>─────────────<br/>• Query LH Schedules<br/>• Check seat availability<br/>• Same day / next day"]
        S2["Hotel + Next Day<br/>─────────────<br/>• Nearby hotels (Maps)<br/>• Next morning flights<br/>• Transfer logistics"]
        S3["Ground Transport<br/>─────────────<br/>• Train routes (Maps)<br/>• Bus alternatives<br/>• Drive time estimates"]
        S4["Alt. Airport Route<br/>─────────────<br/>• Nearby airports<br/>• Connecting flights<br/>• Total journey time"]
    end

    subgraph Presentation
        RANK["Option Ranker"]
        EXPLAIN["Gemini Explainer"]
    end

    S1 --> RANK
    S2 --> RANK
    S3 --> RANK
    S4 --> RANK
    RANK --> EXPLAIN
```

</div>
<div>

### Deliverables

<v-clicks>

- **4 strategy modules** — flight, hotel, ground, alt-airport
- Each module callable independently
- Option ranking by arrival time & disruption level
- **Gemini-powered explanations** with Google Search/Maps grounding
- Returns 3-4 concrete options per passenger

</v-clicks>

</div>
</div>

<!--
Each strategy module can be developed and tested independently. Gemini generates plain-language explanations grounded in real search results.
-->

---

# State Manager

<div class="grid grid-cols-2 gap-8">
<div>

```mermaid {scale: 0.55}
graph TD
    subgraph Core["Core State"]
        PAX_REG["Passenger Registry<br/>─────────────<br/>• Original itinerary<br/>• Current status<br/>• Denial count"]
        WISH["Wish Tracker<br/>─────────────<br/>• Selected option<br/>• Ranked preferences<br/>• Timestamps"]
        PRIO["Priority Queue<br/>─────────────<br/>• Default: timestamp order<br/>• +1 denial: above first-choice<br/>• +2 denials: highest priority"]
    end

    subgraph Logic["Business Logic"]
        APPROVE["Approval Handler"]
        CONFLICT["Conflict Notifier"]
        DENY["Denial Handler"]
    end

    PAX_REG --> APPROVE
    WISH --> APPROVE
    PRIO --> APPROVE
    APPROVE --> CONFLICT
    CONFLICT --> DENY
```

</div>
<div>

### Deliverables

<v-clicks>

- In-memory passenger state store (clear interfaces)
- Wish tracking with ranked preference support
- **Priority queue** — denial-based escalation
- Post-approval conflict notification (simplified)
- Approval/denial handlers with real-time dispatch

</v-clicks>

</div>
</div>

<!--
Priority escalation ensures denied passengers don't get stuck at the back of the queue.
Post-approval conflict handling is simplified: just mark conflicting options unavailable and notify.
-->

---
layout: section
---

# Data Flow

End-to-end workflow

---

# End-to-End Sequence

```mermaid {scale: 0.48}
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

<!--
The full happy path: disruption → options → passenger chooses → gate agent approves/denies → conflict resolution.
Denial triggers priority escalation and option regeneration.
-->

---
layout: section
---

# Client Applications

---

# Gate Agent Dashboard (React) — Primary Product

```mermaid {scale: 0.7}
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
```

<v-click>

**Key:** React SPA · WebSocket real-time · Priority-sorted wish stream · One-click approval workflow

</v-click>

<!--
This is the primary demo product. The dashboard gives gate agents a real-time view of passenger wishes and lets them approve or deny with one click.
-->

---

# Passenger App (Kotlin Multiplatform)

<div class="grid grid-cols-2 gap-8">
<div>

```mermaid {scale: 0.6}
graph TD
    subgraph Screens["App Screens"]
        S1["Disruption Alert<br/>─────────────<br/>• What happened<br/>• Why (plain language)<br/>• What it means for you"]
        S2["Options View<br/>─────────────<br/>• Default rebook (if any)<br/>• 3-4 alternatives<br/>• Details per option"]
        S3["Preference Selector<br/>─────────────<br/>• Single choice<br/>• Or ranked preferences<br/>• Submit as wish"]
        S4["Status Tracker<br/>─────────────<br/>• Waiting for approval<br/>• Approved + next steps<br/>• Denied + new options"]
    end

    S1 --> S2 --> S3 --> S4
    S4 -.->|denied| S2
```

</div>
<div>

### Targets

- Android (native)
- iOS (native)
- Web (Compose for Web)

### Deliverables

<v-clicks>

- Compose Multiplatform UI
- WebSocket push notifications
- API client for backend
- 4 screens: alert → options → preference → status

</v-clicks>

</div>
</div>

<!--
The passenger app uses Kotlin Multiplatform to target all three platforms from a single codebase.
Denied passengers loop back to the options view with regenerated alternatives.
-->

---
layout: section
---

# API Contract

---
layout: two-cols-header
---

# Core Data Types

::left::

```mermaid {scale: 0.42}
classDiagram
    class Disruption {
        +string id
        +string type
        +string flightNumber
        +string origin
        +string destination
        +string reason
        +datetime detectedAt
        +string[] affectedPassengerIds
    }

    class Passenger {
        +string id
        +string name
        +string bookingRef
        +Itinerary originalItinerary
        +string status
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

    Passenger --> Itinerary
    Itinerary --> Segment
    Disruption --> Passenger
```

::right::

```mermaid {scale: 0.42}
classDiagram
    class Option {
        +string id
        +string type
        +string summary
        +string description
        +object details
        +bool available
    }

    class Wish {
        +string id
        +string passengerId
        +string selectedOptionId
        +string[] rankedOptionIds
        +datetime submittedAt
        +string status
    }

    Passenger --> Wish
    Wish --> Option
```

<v-click>

**Option types:** `rebook` · `hotel` · `ground` · `alt_airport`

**Wish status:** `pending` → `approved` | `denied`

**Passenger status:** `unaffected` → `notified` → `chose` → `approved` | `denied`

</v-click>

<!--
These types are the shared contract between backend and both frontends. Defined upfront so teams can work in parallel.
-->

---

# WebSocket Events & REST Endpoints

<div class="grid grid-cols-2 gap-8">
<div>

### WebSocket Events

```mermaid {scale: 0.5}
graph LR
    subgraph Server to Dashboard
        E1["new_wish"]
        E2["wish_approved"]
        E3["wish_denied"]
        E4["disruption_created"]
    end

    subgraph Server to Passenger App
        E5["options_available"]
        E6["wish_confirmed"]
        E7["wish_rejected"]
        E8["options_updated"]
    end
```

</div>
<div>

### REST Endpoints

| Method | Path | Used by |
|--------|------|---------|
| POST | `/disruptions/simulate` | Simulator |
| GET | `/disruptions/:id` | Dashboard |
| GET | `/disruptions/:id/passengers` | Dashboard |
| GET | `/passengers/:id/options` | Pax App |
| POST | `/passengers/:id/wish` | Pax App |
| POST | `/wishes/:id/approve` | Dashboard |
| POST | `/wishes/:id/deny` | Dashboard |

</div>
</div>

<!--
WebSocket for real-time push, REST for request/response. Dashboard is WebSocket-primary, passenger app uses both.
-->

---
layout: section
---

# Implementation Roadmap

---

# Parallel Implementation Strategy

All three components built **in parallel from day one**. Backend starts with hardcoded mock responses.

```mermaid {scale: 0.65}
gantt
    title Implementation Roadmap (Parallel)
    dateFormat X
    axisFormat %s

    section Phase 1 — Foundation
    API contract + shared types        :p1, 0, 1
    Disruption simulator (mock trigger):p2, 0, 1
    Backend scaffolding + mock API     :p3, 0, 2
    State Manager (in-memory)          :p4, 0, 2
    Passenger App scaffold + screens   :p5, 0, 2
    Gate Agent Dashboard scaffold      :p6, 0, 2

    section Phase 2 — Core Features
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

<!--
Mock-first approach lets all teams move in parallel. Real API integrations are swapped in Phase 4.
-->

---

# Technology Map

```mermaid {scale: 0.7}
graph LR
    subgraph Languages
        PY["Python 3.14"]
        KT["Kotlin (KMP)"]
        TS["TypeScript"]
    end

    subgraph Frameworks
        FAST["FastAPI"]
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
```

<!--
Three languages, three frameworks, three protocols. Gemini with grounding is the AI backbone.
-->

---
layout: end
---

# Soft Landing

Let's build it.
