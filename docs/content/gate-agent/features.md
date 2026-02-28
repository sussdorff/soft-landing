# Dashboard Features

Detailed reference for each feature of the Gate Agent Dashboard.

## Overview Panel

The collapsible overview panel at the top of the dashboard shows aggregate stats for the selected disruption:

| Metric | Description |
|--------|-------------|
| Total Affected | Number of passengers impacted by this disruption |
| Wishes Pending | Submitted preferences awaiting agent action |
| Resolved | Passengers with an approved resolution |
| Denied | Passengers whose preference was denied (re-prioritized) |

The panel updates in real-time via WebSocket — no refresh needed.

## Flight Selector

The dropdown in the top bar lets you switch between active disruptions. Each entry shows:

- Flight number and route (e.g., LH 1234 MUC → JFK)
- Disruption type (cancellation, diversion, delay, gate change)
- Number of affected passengers

## Flight Overview

The main passenger roster for the selected disruption. Each row shows:

| Column | Content |
|--------|---------|
| Name | Passenger full name |
| PNR | Booking reference code |
| Status | Current state: notified, chose, approved, denied |
| Priority | Current priority level (escalates after denials) |
| Action | Resolve button to jump to their wish |

Click any row to open the full **Passenger Profile**.

### Sorting

Passengers are sorted by:

1. Priority (highest first — denied passengers float up)
2. Status (pending wishes before resolved)
3. Name (alphabetical within same priority/status)

## Wish Stream

Real-time feed of incoming passenger preferences. This is where the core approval workflow happens.

### Wish Card

Each card displays:

- **Passenger info** — name, PNR, denial count
- **Selected option** — summary of what they want (flight, hotel, transport)
- **Priority badge** — visual indicator of urgency
- **Action buttons** — Approve (green) and Deny (red)

### Sorting

Wishes are ordered by:

1. Priority descending (denied passengers first)
2. Submission time ascending (first come, first served within same priority)

### Actions

- **Approve** — one click confirms the option. Conflicting options for other passengers are automatically marked unavailable.
- **Deny** — opens a reason dialog. After denial, the passenger is bumped in priority and may receive new options.

## Passenger Profile

Full detail view opened by clicking a passenger anywhere in the dashboard.

### Sections

**Itinerary**
: All flight segments in the original booking, with departure/arrival times and airports.

**Available Options**
: All options generated for this passenger with details:

- Rebook — flight number, route, departure time, estimated arrival
- Hotel — hotel name, address, checkout time, next-day flight
- Ground Transport — mode (train/bus), route, duration, departure time
- Alternative Airport — destination airport, flight + ground transfer details

**Wish History**
: Timeline of all submitted wishes with:

- Selected option
- Submission timestamp
- Status (pending, approved, denied)
- Denial reason (if applicable)

**Status**
: Current passenger state, denial count, and priority level.

## Search

The search bar in the top bar supports:

| Query Type | Example |
|------------|---------|
| Passenger name | `Mueller` |
| Booking reference | `ABC123` |
| Airport code | `MUC` |
| Flight number | `LH1234` |

Search filters across all active disruptions, not just the currently selected one.
