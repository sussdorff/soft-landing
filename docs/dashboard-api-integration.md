# Dashboard — API Integration Reference

This document describes every feature of the Gate Agent Dashboard, which backend API endpoints it calls, and where gaps exist that still need implementing.

---

## Architecture Overview

```
Dashboard (React SPA)
  │
  ├── HTTP REST ──► FastAPI backend (https://softlanding.sussdorff.de)
  │
  └── WebSocket ──► /ws/dashboard/{disruption_id}
                     (real-time wish events)
```

**Env vars:**
| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `https://softlanding.sussdorff.de` | REST API base |
| `VITE_WS_URL` | `wss://softlanding.sussdorff.de` | WebSocket base |
| `VITE_USE_MOCKS` | `false` | Use mock adapter instead of real API |

---

## 1. Load Disruptions (Flight Selector)

**What it does:** On startup, the dashboard loads available disruptions so the gate agent can pick which flight to manage via a searchable dropdown.

**API call:**
```
GET /disruptions/dis-snowstorm-001
```

**Gap:** There is no `GET /disruptions` list endpoint. The dashboard hardcodes a fallback fetch of `dis-snowstorm-001` and tracks any disruption it has seen in a client-side Map. A proper list endpoint is needed for the flight selector to work with real data.

**Needed endpoint:**
```
GET /disruptions
→ Response: Disruption[]
```

---

## 2. Load Disruption Details

**What it does:** When a disruption is selected, fetches its full details (flight number, type, origin, destination, reason, affected passengers).

**API call:**
```
GET /disruptions/{disruption_id}
→ Response: Disruption
```

**Status:** Exists and works.

---

## 3. Load Passengers

**What it does:** Fetches all passengers affected by the selected disruption. Displayed in the Flight Overview table and used to compute stats in the Overview Panel.

**API call:**
```
GET /disruptions/{disruption_id}/passengers
→ Response: Passenger[]   (sorted by priority desc, name asc)
```

**Status:** Exists and works.

**Note:** The backend returns `originalItinerary` as a flat `Segment[]`. The dashboard wraps it into `{ segments: Segment[] }` via an adapter transform.

---

## 4. Load Options (Per-Passenger)

**What it does:** Loads rebooking/hotel/ground transport options for every affected passenger. Used in the Flight Overview (resolve dropdown) and Wish Stream (show what the passenger chose).

**API call:**
```
GET /passengers/{passenger_id}/options
→ Response: Option[]
```

**Workaround:** The backend only has per-passenger options. The dashboard fetches the passenger list first, then batch-fetches options for each passenger (10 in parallel). This means `N/10` sequential rounds of requests.

**Needed endpoint:**
```
GET /disruptions/{disruption_id}/options
→ Response: Record<passengerId, Option[]>
```

This would replace N+1 requests with a single call.

---

## 5. Load Wishes

**What it does:** Fetches all wishes (passenger preferences) for the selected disruption. Split into pending (actionable) and resolved (approved/denied) lists.

**API call:**
```
GET /wishes?disruption_id={disruption_id}
→ Response: Wish[]
```

**Status:** Exists and works.

---

## 6. Approve Wish

**What it does:** Gate agent approves a passenger's wish. Updates passenger status to APPROVED.

**API call:**
```
POST /wishes/{wish_id}/approve
→ Response: updated Wish
```

**Status:** Exists and works.

**Side effects:** Backend broadcasts `wish_approved` via WebSocket. Dashboard receives it and re-fetches passenger list to update status badges.

---

## 7. Deny Wish

**What it does:** Gate agent denies a passenger's wish with a mandatory reason. Updates passenger status to DENIED, increments denial count, adjusts priority.

**API call:**
```
POST /wishes/{wish_id}/deny
Body: { "reason": string }
→ Response: updated Wish
```

**Status:** Exists and works.

**Side effects:** Backend broadcasts `wish_denied` via WebSocket. Dashboard re-fetches passenger list.

---

## 8. Manual Resolution

**What it does:** Gate agent resolves a passenger directly by choosing an option on their behalf (without waiting for the passenger to submit a wish via the mobile app). Creates a wish and immediately approves it.

**API calls (composed):**
```
1. POST /passengers/{passenger_id}/wish
   Body: { "disruptionId": string, "selectedOptionId": string, "rankedOptionIds": [optionId] }
   → Response: Wish

2. POST /wishes/{wish_id}/approve
   → Response: updated Wish
```

**Status:** Works via composition. Both endpoints exist. The dashboard chains them: create wish → approve.

**Possible improvement:** A dedicated `POST /passengers/{id}/resolve` endpoint that atomically creates and approves could avoid race conditions if the backend ever adds auto-processing between steps.

---

## 9. Passenger Profile

**What it does:** Modal showing full passenger details — identity, itinerary, available options, and wish history. Triggered by clicking any passenger name.

**API call:**
```
GET /passengers/{passenger_id}/profile
→ Response: { passenger: Passenger, options: Option[], wishes: Wish[], disruptions: Disruption[] }
```

**Status:** Exists and works.

**Note:** The `disruptions` field is returned by the backend but not currently displayed in the dashboard profile modal.

---

## 10. WebSocket — Real-Time Events

**Connection:**
```
wss://softlanding.sussdorff.de/ws/dashboard/{disruption_id}
```

Connected when a disruption is selected. Auto-reconnects every 3 seconds on disconnect.

**Message envelope:**
```json
{
  "type": "event_type",
  "timestamp": "2026-02-28T12:00:00Z",
  "data": { ... }
}
```

### Events the dashboard listens for:

| Event | Data | Dashboard action |
|---|---|---|
| `new_wish` / `wish_submitted` | `{ wishId, passengerId, selectedOptionId }` | Prepend to wish stream |
| `wish_approved` | `{ wishId, selectedOptionId }` | Update wish status, re-fetch passengers |
| `wish_denied` | `{ wishId, reason }` | Update wish status, re-fetch passengers |

### Events defined but not handled by the dashboard:

| Event | Data | Notes |
|---|---|---|
| `disruption_created` | `{ disruptionId, type, flightNumber, affectedPassengers }` | Could be used to auto-add new disruptions to the flight selector |
| `options_updated` | — | Could trigger re-fetch of options if backend updates them |

**Gap:** The dashboard never re-fetches options after initial load. If the backend updates available options (e.g., a rebooking flight sells out), the dashboard won't reflect it until the page is refreshed.

---

## 11. Passenger Status Endpoint (Unused)

The backend exposes a lightweight status check that the dashboard does not currently use:

```
GET /passengers/{passenger_id}/status
→ Response: { passengerId, name, status, denialCount, priority }
```

Could be useful for polling individual passenger status without refetching the full list.

---

## 12. Disruption Ingestion (Unused by Dashboard)

The backend supports creating disruptions from external events:

```
POST /disruptions/ingest
Body: { flight_number, origin, destination, reason, status_code?, explanation? }
→ Response: Disruption
```

```
POST /disruptions/simulate
Body: { scenario: "munich_snowstorm" | "diversion" }
→ Response: Disruption
```

The dashboard does not call these — they're triggered externally or via API tools.

---

## Summary: Gaps & Needed Work

| # | Gap | Impact | Priority |
|---|---|---|---|
| 1 | **No `GET /disruptions` list endpoint** | Flight selector only loads hardcoded `dis-snowstorm-001` | High |
| 2 | **No bulk options endpoint** | N+1 requests to load options for all passengers | Medium |
| 3 | **`disruption_created` WebSocket event not handled** | New disruptions don't appear in the flight selector until page refresh | Medium |
| 4 | **`options_updated` WebSocket event not handled** | Stale option availability (e.g., sold-out rebookings still show as available) | Low |
| 5 | **No atomic resolve endpoint** | Manual resolution uses two sequential API calls (create wish + approve) | Low |
| 6 | **Backend `disruptions` field from profile not displayed** | Profile modal doesn't show which other disruptions affect a passenger | Low |
