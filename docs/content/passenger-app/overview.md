# Passenger App — Overview

The Passenger App guides disrupted travelers through their rebooking options. When a disruption affects your flight, the app provides clear information about what happened and what you can do next.

## Access

The app is available at:

```
https://softlanding.sussdorff.de/app/
```

It runs on Android, iOS, and web browsers via Kotlin Multiplatform.

## Identification

To access your disruption information, enter:

- **Booking reference (PNR)** — the 6-character code from your booking confirmation
- **Last name** — as it appears on your booking

This links you to your passenger record and any active disruptions.

## What You'll See

Once identified, the app shows:

1. **Disruption summary** — what happened, in plain language (e.g., "Heavy snowfall in Munich has caused your connecting flight LH 456 to be cancelled")
2. **Your options** — 3–4 alternatives generated automatically
3. **Status tracker** — real-time updates as the gate agent reviews your preference

## Real-Time Connection

The app maintains a WebSocket connection to the backend. You'll receive instant updates:

- When new options become available
- When the gate agent approves your wish
- When a wish is denied (with the reason and new options)
- When your priority changes

No manual refresh needed — the app stays current.

## Next Steps

- [Disruption Flow](disruption-flow.md) — Step-by-step walkthrough of the passenger experience
