# ReRoute — Soft Landing

**A single gate agent can handle 200 disrupted passengers in minutes instead of hours.**

ReRoute is a real-time disruption management system that connects gate agents and passengers during flight disruptions. When things go wrong — cancellations, diversions, delays — ReRoute gives agents an operational command center and passengers a clear path to resolution.

## How It Works

When a disruption is detected, ReRoute automatically:

1. Identifies all affected passengers and their connecting flights
2. Generates rebooking options (alternative flights, hotels, ground transport)
3. Notifies passengers with a plain-language explanation of what happened
4. Streams passenger preferences to the gate agent in real-time
5. Lets the agent approve or deny wishes with full visibility into cascading impacts

## Two User Types

### For Gate Agents

The **Gate Agent Dashboard** is an operational command center at [`/dashboard/`](https://softlanding.sussdorff.de/dashboard/). It provides:

- Real-time overview of all affected passengers
- Priority-sorted wish stream with one-click approve/deny
- Passenger profiles with full itinerary and disruption history
- Search by name, booking reference, airport, or flight number

[:material-monitor-dashboard: Gate Agent Guide](gate-agent/overview.md){ .md-button .md-button--primary }

### For Passengers

The **Passenger App** guides disrupted travelers through their options. Passengers receive:

- Clear, plain-language disruption notifications
- Automatically generated alternatives ranked by fit
- Real-time status updates as the gate agent processes their request
- Priority escalation if their first choice is denied

[:material-cellphone: Passenger App Guide](passenger-app/overview.md){ .md-button }

## API Reference

ReRoute exposes a REST API and WebSocket endpoints for real-time communication.

[:material-api: API Reference](api.md){ .md-button }

---

*Built for the "Innovate the Skies & Beyond" hackathon (Lufthansa + Google), February 2026.*
