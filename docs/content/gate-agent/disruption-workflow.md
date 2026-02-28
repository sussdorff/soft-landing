# Disruption Workflow

This guide walks through the complete lifecycle of handling a disruption from the gate agent's perspective.

## 1. Disruption Detected

When a disruption occurs (cancellation, diversion, delay, or gate change), the system automatically:

- Creates a disruption record with type and reason
- Identifies all affected passengers by matching flight segments
- Generates 3–4 rebooking options per passenger
- Sends push notifications to affected passengers
- Updates the dashboard in real-time

!!! info "Automatic option generation"
    Options are generated instantly based on the disruption type: alternative flights, hotel + next-day rebooking, ground transport (train/bus), or routing via an alternative airport.

## 2. Review the Overview

Switch to the disrupted flight using the **flight selector** in the top bar. The **Overview Panel** shows:

- **Total affected** — number of passengers impacted
- **Wishes pending** — passengers who have submitted a preference but await approval
- **Resolved** — passengers with an approved resolution
- **Denied** — passengers whose preference was denied (these are re-prioritized)

## 3. Monitor the Wish Stream

As passengers open the app and select their preferred option, wishes appear in the **Wishes** tab. Wishes are sorted by:

1. **Priority** — denied passengers appear first (higher priority after each denial)
2. **Timestamp** — among equal priority, earlier submissions come first

Each wish card shows:

- Passenger name and booking reference
- Selected option summary (e.g., "Rebook: LH 98 → FRA, dep 14:30")
- Priority indicator (escalated after denials)
- Denial count if applicable

## 4. Approve or Deny

### Approve

Click **Approve** to confirm the passenger's preferred option. This:

- Marks the wish as approved
- Updates the passenger's status to `approved`
- Notifies the passenger via WebSocket
- Marks conflicting options (e.g., same seat on same flight) as unavailable for other passengers

### Deny

Click **Deny** to reject the preference. You'll be prompted for a reason. This:

- Marks the wish as denied with the stated reason
- Notifies the passenger with the denial reason
- **Bumps the passenger's priority** — after 1 denial they rank above first-choice passengers; after 2 denials they get highest priority
- Regenerates options if the denied option is no longer available

!!! warning "Priority escalation"
    Denied passengers automatically move up in the queue. After two denials, a passenger gets the highest priority level. Handle denials carefully — they cascade.

## 5. Resolve Edge Cases

For complex situations, open the **Passenger Profile** by clicking on a passenger row:

- Review their full itinerary (all flight segments)
- See all available options with details (times, hotels, transport modes)
- Check their wish history and previous denial reasons
- Assess their current priority level

## 6. Monitor Progress

The Overview Panel updates in real-time. A fully resolved disruption shows:

- All passengers either approved or in the process of resubmitting
- No pending wishes remaining
- Denied passengers re-prioritized and actively being processed

---

## Quick Reference

| Action | Result |
|--------|--------|
| Approve wish | Passenger confirmed, conflicting options removed |
| Deny wish | Passenger priority bumped, new options generated |
| 1 denial | Passenger ranks above first-choice passengers |
| 2 denials | Passenger gets highest priority |
| Click passenger | Opens full profile with itinerary and history |
