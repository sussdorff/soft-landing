# Gate Agent Dashboard — Overview

The Gate Agent Dashboard is the operational command center for managing disrupted passengers. It runs at [`/dashboard/`](https://softlanding.sussdorff.de/dashboard/) and provides real-time visibility into passenger status, wishes, and resolution progress.

## Access

Open the dashboard in any modern browser:

```
https://softlanding.sussdorff.de/dashboard/
```

No login required — the dashboard connects automatically via WebSocket for real-time updates.

## Layout

The dashboard is organized into three main areas:

### Top Bar

- Flight selector — switch between active disruptions
- Search — find passengers by name, booking reference (PNR), airport code, or flight number

### Main Content Area

Tabs for different views:

| Tab | Purpose |
|-----|---------|
| **Overview** | At-a-glance stats: total affected, wishes pending, resolved, denied |
| **Flight Overview** | All affected passengers with status, itinerary, and actions |
| **Wishes** | Real-time stream of incoming passenger preferences |

### Passenger Profile

Click any passenger to open their full profile:

- Original itinerary (all segments)
- Available options with details
- Wish history and denial reasons
- Current status and priority level

## Real-Time Updates

The dashboard maintains a persistent WebSocket connection to the backend. Updates appear instantly:

- New wishes stream in as passengers submit preferences
- Status changes (approved, denied) reflect immediately
- Priority reordering happens automatically after denials
- No manual refresh needed

## Next Steps

- [Disruption Workflow](disruption-workflow.md) — Step-by-step guide for handling a disruption
- [Features](features.md) — Detailed reference for each dashboard feature
