# API Reference

ReRoute exposes a REST API for disruption management and WebSocket endpoints for real-time communication. Full interactive documentation is available via Swagger UI.

**Live API docs:** [`/api/docs`](https://softlanding.sussdorff.de/api/docs){ target=_blank }

**OpenAPI spec:** [`/api/openapi.json`](https://softlanding.sussdorff.de/api/openapi.json){ target=_blank }

## REST Endpoints

### Disruptions

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/disruptions/simulate` | Inject a mock disruption scenario (resets DB, seeds data) |
| `GET` | `/disruptions/{id}` | Get disruption details and explanation |
| `GET` | `/disruptions/{id}/passengers` | List affected passengers sorted by priority |
| `POST` | `/disruptions/ingest` | Ingest a raw disruption event (engine classifies and processes) |

### Passengers

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/passengers/{id}/disruptions` | List active disruptions affecting a passenger |
| `GET` | `/passengers/{id}/options` | Get available rebooking options |
| `GET` | `/passengers/{id}/status` | Current state: status, denial count, priority |
| `GET` | `/passengers/{id}/profile` | Full profile: itinerary, wishes, options, history |
| `POST` | `/passengers/{id}/wish` | Submit ranked preference(s) |

### Wishes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/wishes` | List wishes (filter by `?disruption_id=`) |
| `POST` | `/wishes/{id}/approve` | Approve a wish (marks option taken, notifies passenger) |
| `POST` | `/wishes/{id}/deny` | Deny with reason (bumps priority, regenerates options) |

## WebSocket Endpoints

Two WebSocket endpoints provide real-time updates:

### Dashboard WebSocket

```
wss://softlanding.sussdorff.de/ws/dashboard/{disruption_id}
```

Used by the Gate Agent Dashboard. Events received:

| Event | Payload | Trigger |
|-------|---------|---------|
| `wish_submitted` | Wish object | Passenger submits a preference |
| `wish_approved` | Wish object | Agent approves a wish |
| `wish_denied` | Wish object + reason | Agent denies a wish |

### Passenger WebSocket

```
wss://softlanding.sussdorff.de/ws/passenger/{passenger_id}
```

Used by the Passenger App. Events received:

| Event | Payload | Trigger |
|-------|---------|---------|
| `options_available` | List of options | Options generated after disruption |
| `wish_confirmed` | Confirmed wish details | Agent approved the wish |
| `wish_rejected` | Denial reason + new options | Agent denied the wish |

## Disruption Types

| Type | Code | Description |
|------|------|-------------|
| Cancellation | `CANCELLATION` | Flight cancelled entirely |
| Diversion | `DIVERSION` | Flight diverted to different airport |
| Delay | `DELAY` | Significant delay affecting connections |
| Gate Change | `GATE_CHANGE` | Gate reassignment |

## Option Types

| Type | Code | Description |
|------|------|-------------|
| Rebook | `REBOOK` | Alternative flight to destination |
| Hotel | `HOTEL` | Overnight stay + next-day flight |
| Ground Transport | `GROUND_TRANSPORT` | Train or bus to destination |
| Alternative Airport | `ALT_AIRPORT` | Flight to nearby airport + ground transfer |

## Passenger Statuses

| Status | Meaning |
|--------|---------|
| `UNAFFECTED` | No active disruption |
| `NOTIFIED` | Disruption notification sent |
| `CHOSE` | Preference submitted, awaiting approval |
| `APPROVED` | Wish approved by gate agent |
| `DENIED` | Wish denied, new options available |
