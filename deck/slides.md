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

### Passenger Disruption Management

<br>

**Passenger app** (KMP) · **Gate agent dashboard** (React) · **Backend** (Python)

---

# The Problem

When flights break, passengers crowd the gate desk and agents drown in manual rebooking — one passenger at a time, while 200 others wait.

<br>

### No visibility into cascading impact

- Agent approves a seat — but that seat was the last option for three other passengers
- Denied passengers go to the back of the line and start over
- No way to see the big picture or prioritize

---

# Soft Landing

An **operational command center** for gate agents backed by a passenger self-service app.

<br>

- **Passengers** get a disruption explanation and choose from AI-generated options (rebook, hotel, ground transport, alt airport)
- **Preferences stream** into the gate agent's dashboard in real time
- **Gate agent stays in control** — human-in-the-loop approval for every decision
- **AI does the heavy lifting** — Gemini generates options and plain-language explanations grounded in live data (flights, maps, search)

---

# How It Works

```mermaid {scale: 0.7}
graph LR
    A["Disruption detected"] --> B["Options generated<br/>per passenger"]
    B --> C["Passenger picks<br/>preference"]
    C --> D["Wish streams to<br/>gate agent"]
    D --> E{Approve?}
    E -->|Yes| F["Confirmed +<br/>next steps"]
    E -->|No| G["Priority bumped,<br/>new options"]
    G --> C
```

<br>

Passenger choice = **wish**, not booking. Gate agent has final say. Denied passengers get escalated priority — they don't go to the back of the line.

---

# System Architecture

```mermaid {scale: 0.65}
graph TB
    subgraph External["External Services"]
        LH["Lufthansa APIs"]
        GEMINI["Gemini 3.0 + Grounding"]
        GOOGLE["Google Maps / Search"]
    end

    subgraph Backend["Backend (Python)"]
        DE["Disruption Engine"]
        OG["Option Generator"]
        SM["State Manager"]
        WS["WebSocket"]
        API["REST API"]
    end

    subgraph Clients
        DASH["Gate Agent Dashboard (React)"]
        PAX["Passenger App (KMP)"]
    end

    DE -->|context| OG
    OG -->|options| SM
    SM <--> WS
    SM <--> API
    LH --> OG
    GEMINI --> OG
    GOOGLE --> OG
    WS <--> DASH
    WS <--> PAX
    API <--> PAX
```

<!--
Three layers: external APIs, backend pipeline, two client apps.
-->

---

# Backend Pipeline

```mermaid {scale: 0.8}
graph LR
    DE["Disruption Engine<br/>detect & classify"] --> OG["Option Generator<br/>4 resolution strategies"] --> SM["State Manager<br/>wishes, priority, conflicts"]
```

<br>

| Component | Role |
|-----------|------|
| **Disruption Engine** | Receives events (simulator / MQTT), identifies affected passengers |
| **Option Generator** | Queries LH + Maps + Gemini, produces ranked options with explanations |
| **State Manager** | Tracks wishes, handles approvals/denials, escalates priority on denial |

---

# Data Flow

```mermaid {scale: 0.65}
sequenceDiagram
    participant DE as Disruption Engine
    participant OG as Option Generator
    participant SM as State Manager
    participant PAX as Passenger App
    participant GA as Dashboard

    DE->>OG: Affected passengers
    OG->>SM: Ranked options per passenger
    SM->>PAX: options_available (WS)
    SM->>GA: disruption_created (WS)
    PAX->>SM: Submit wish (REST)
    SM->>GA: new_wish (WS)
    GA->>SM: Approve / Deny (REST)
    SM->>PAX: Confirmed or new options (WS)
```

---

# Gate Agent Dashboard

React SPA with WebSocket real-time updates

| View | Purpose |
|------|---------|
| **Overview** | All affected passengers, connection risk stats |
| **Wish Stream** | Live feed of passenger preferences, sorted by priority |
| **Approval Panel** | One-click approve, deny with reason |
| **Manual Resolution** | Full passenger profile and override tools |

---

# Passenger App

Kotlin Multiplatform → Android, iOS, Web

```mermaid {scale: 0.7}
graph LR
    S1["Alert"] --> S2["Options"] --> S3["Choose"] --> S4["Status"]
    S4 -.->|denied| S2
```

<br>

- **Alert** — plain-language explanation of disruption (Gemini-generated)
- **Options** — 3-4 alternatives: rebook, hotel, ground transport, alt airport
- **Choose** — single pick or ranked preferences, submitted as wish
- **Status** — tracks approval; denial loops back with new options

---

# API Contract

<div class="grid grid-cols-2 gap-8">
<div>

### Core Types

- **Disruption** — type, flight, affected passengers
- **Passenger** — itinerary, status, denial count, priority
- **Option** — type (`rebook` | `hotel` | `ground` | `alt_airport`), availability
- **Wish** — selected option, status (`pending` → `approved` | `denied`)

</div>
<div>

### Endpoints

| Method | Path |
|--------|------|
| POST | `/disruptions/simulate` |
| GET | `/passengers/:id/options` |
| POST | `/passengers/:id/wish` |
| POST | `/wishes/:id/approve` |
| POST | `/wishes/:id/deny` |

WebSocket events: `disruption_created`, `new_wish`, `options_available`, `wish_confirmed`, `wish_rejected`, `options_updated`

</div>
</div>

---

# Technology Stack

```mermaid {scale: 0.8}
graph LR
    PY["Python · FastAPI"] --- REST["REST + WebSockets"]
    KT["Kotlin · Compose MP"] --- REST
    TS["TypeScript · React"] --- REST
    PY --- GEM["Gemini 3.0<br/>Search + Maps Grounding"]
```

<br>

| Layer | Choice |
|-------|--------|
| Backend | Python 3.14, FastAPI |
| Passenger App | Kotlin Multiplatform (Compose) |
| Dashboard | React, TypeScript |
| AI | Gemini 3.0 with Google Search & Maps grounding |
| Protocols | REST, WebSockets, MQTT (later) |

---
layout: end
---

# Soft Landing

Let's build it.
