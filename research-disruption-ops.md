# Research: AI Agents for Airline Disruption Management

> Research for "Innovate the Skies & Beyond" hackathon, 2026-02-27

---

## Executive Summary

Normal airline ops are heavily optimized. The opportunity is in **disruption recovery** — the chaotic period when weather, ATC, maintenance, or crew issues cascade through the network. Current tools are siloed (aircraft recovery ≠ crew recovery ≠ passenger recovery), coordination between airlines/airports/ground handlers happens via phone calls, and decisions must be made in minutes across thousands of variables.

The hackathon gives us: Lufthansa Flight Ops API (real-time flight status, delays, cancellations, push notifications) + Gemini Grounding (Google Search for real-time context, Google Maps for routing/location). The sweet spot is combining these to build an **agent that augments OCC decision-making during disruptions**.

---

## 1. Why Disruptions — The Business Case

### Per-Minute Cost of Delays (Eurocontrol 2022)
| Phase | All delays | Short delays (<30 min) |
|-------|-----------|----------------------|
| At gate | EUR 166/min | EUR 45/min |
| Taxiing | EUR 182/min | EUR 62/min |
| En-route | EUR 212/min | EUR 89/min |

### EU261 Compensation Exposure
- EUR 250/pax (< 1,500 km)
- EUR 400/pax (1,500–3,500 km)
- EUR 600/pax (> 3,500 km)
- Single cancelled long-haul (300 pax) = **EUR 180,000 in compensation alone**
- Industry-wide: ~EUR 5B/year in actual payouts

### Total Industry Cost
- **$60–67.5B globally** in disruption costs per year
- ~8% of total airline revenue
- ~200M passengers affected annually (US alone)

---

## 2. What Actually Happens During a Disruption

### The Cascade Mechanics
An aircraft flies 4–6 legs/day. A 45-min delay on leg 1 compounds through every subsequent leg. Schedule buffers (15–30 min) are consumed by the first disruption.

**Crew legality** is the hidden killer: EASA limits flight duty to ~13 hours max. A 2-hour delay at 8pm pushes crew past their legal limit, grounding not just that flight but every subsequent flight that crew was rostered for. Commander's discretion gives +2 hours but then increases the following rest requirement, potentially killing next day's roster.

**Hub wave destruction**: Lufthansa runs 5–6 connection waves/day at Frankfurt. When inbound flights in a wave arrive late, the entire connecting wave is compromised. Missing a wave = 2–4 hour wait (or overnight if last wave).

**Ground handler surge**: When multiple delayed flights arrive simultaneously, there aren't enough handlers/tugs/de-icing trucks. A 10-min delay becomes 60 min because resources were re-allocated.

### The Southwest 2022 Meltdown — What Systemic Failure Looks Like
- 16,700 flights cancelled over 10 days (70% of schedule)
- 2 million passengers stranded
- Root cause: crew tracking system collapsed — airline literally lost track of where crew members were
- Crews had to call scheduling by phone, overwhelming phone lines
- $1.3B spent on IT modernization afterward

---

## 3. Decision-Making Bottlenecks in the OCC

The Operations Control Center must make decisions under extreme time pressure with **combinatorial explosion** of variables:

### Sequential Recovery That Should Be Simultaneous
Standard approach: "aircraft first → crew → passengers" (sequential). But these are deeply interdependent. Swapping an aircraft may solve the aircraft problem but creates a crew problem (wrong type rating) and passenger problem (smaller aircraft). Research shows this fragmented approach yields "solutions that are feasible but far from optimal" with 10–55% cost reduction achievable through integration.

### Crew Recovery is NP-Hard
A crew controller facing 30 disrupted flights must consider: type ratings, route authorizations, legal rest requirements, physical position of each crew member, union seniority rules for reserve callout, deadhead positioning options. **Often done manually with spreadsheets and phone calls.**

### CTOT Slot Management
Eurocontrol assigns ATFM slots with [-5, +10] minute tolerance. Losing a slot can mean 45+ minutes additional delay. Dispatcher must decide in real-time: can we make the slot? Request a new one? Swap aircraft? Each decision cascades.

### Aircraft Swap Evaluation
Used in ~89% of disruption recovery. Must check: fleet type compatibility, seating config, maintenance status, ETOPS capability, crew type ratings, weight & balance, catering/cleaning status — across dozens of candidates, **within minutes**.

### What's Still Done By Phone
- Calling reserve crew in seniority order, waiting for each to answer
- Coordinating with ground handlers on resource availability
- Inter-airline rebooking
- Maintenance constraint verification across systems

---

## 4. Cross-Stakeholder Information Asymmetries

| Stakeholder | Controls | Blind Spot |
|-------------|----------|------------|
| Airline OCC | Aircraft, crew, pax | ATC flow restrictions, ground handler capacity |
| Eurocontrol | ATFM slots, en-route flow | Airline internal priorities (which flights to protect) |
| Airport | Gates, runways, terminals | Airline recovery plans, turnaround progress |
| Ground handlers | Ramp ops, baggage, de-icing | Updated arrival times (gets them late) |
| ATC (local) | Tower sequencing | Which flights have tight connections |

**A-CDM (Airport Collaborative Decision Making)**: Only 36% of European departures come from A-CDM airports (28 airports as of 2025). Majority still lack systematic airline-airport-ATC-handler data sharing.

**Frankfurt MCT increase**: Raised from 45–50 min to 60 min (March 2025) — direct admission that coordination isn't reliable enough for tighter connections.

---

## 5. Lufthansa Group-Specific Context

### Hub Concentration Risk
- Frankfurt + Munich handle ~60% of LH Group traffic
- Frankfurt: 4 runways, ~126 movements/hour, night curfew 23:00–05:00
- Snow/wind direction changes collapse the wave structure

### Multi-Airline Complexity
- Group: Lufthansa, Swiss, Austrian, Brussels Airlines, ITA Airways, Eurowings
- Different AOCs, crew type ratings, unions, regulatory environments
- Cross-carrier aircraft swaps constrained by all of the above
- Largely independent OCCs — disruption at Vienna doesn't auto-optimize via Munich/Zurich

### Recent Operational Pressures
- 2025 leadership restructuring: split hub oversight (Munich vs Frankfurt) after "decline in quality"
- 4,000 job cuts (~4% of workforce) while aircraft delivery delays continue
- German ATC (DFS) technical issues causing flight delays

---

## 6. Existing Solutions and Their Gaps

| Vendor | Product | Limitation |
|--------|---------|------------|
| Lufthansa Systems | NetLine/Ops++, aiOCC | AI features are new; multi-airline coordination not seamless |
| Amadeus | Altea, Disruption Mgmt | Works in silos — own whitepaper admits modules "mind their own business" |
| Jeppesen (Boeing) | Crew/Flight Planning | Planning tool — disruption recovery needs manual intervention |
| Sabre + Plan3 | Disruption Mgmt | New partnership (2024), still being integrated |
| IBS Software | iFlight | RL-based decision support but limited carrier adoption |

### Universal Gaps
1. **Siloed architecture** — aircraft, crew, passenger recovery are separate modules
2. **No ground handler integration** — airline can't see ground handler capacity
3. **No cross-airline group optimization** — LH Group airlines don't jointly optimize
4. **Phone-based crew callout** — still the norm
5. **Maintenance integration missing** — majority of tools ignore maintenance constraints
6. **No disruption prediction** — reactive only, not predictive

---

## 7. What the Lufthansa API Actually Gives Us

### Available (Public API)
- **Flight status**: delay codes (DL), cancellation (CD), diversion (DV), rerouting (RT)
- **Time deltas**: scheduled vs. estimated vs. actual departure/arrival → delay magnitude calculable
- **Real-time push** (MQTT): cancellations, diversions, reroutes, schedule changes, gate changes
- **Aircraft type** per flight, operating vs. marketing carrier
- **Schedules**: up to 360 days out, including connecting flights
- **Reference data**: airports (with GPS coords), airlines, aircraft types, nearest airports
- **Seat maps**: cabin layout, seat characteristics

### NOT Available (Public API)
- No crew data (restricted to LH staff)
- No maintenance data
- No ground operations data
- No delay reason codes (only that a flight IS delayed, not why)
- No passenger load/capacity
- No historical bulk data

### Key API Endpoints
```
GET /operations/flightstatus/{flightNumber}/{date}
GET /operations/flightstatus/route/{origin}/{destination}/{date}
GET /operations/flightstatus/arrivals/{airportCode}/{fromDateTime}
GET /operations/flightstatus/departures/{airportCode}/{fromDateTime}
GET /operations/customerflightinformation/{flightNumber}/{date}
GET /operations/schedules/{origin}/{destination}/{fromDateTime}
```

### Push Notifications (MQTT)
Topic: `prd/FlightUpdate/{carrier}/{flightNumber}/{date}`

Events: departure/arrival estimates, actual times, gate changes, **cancellations (ASM CNL)**, reinstated flights, diversions, reroutes, schedule changes.

---

## 8. How Gemini Grounding Fills the Gaps

The API gives us flight-level data but no context. Grounding fills in the **why** and the **what's coming**:

### Google Search Grounding
- **Weather disruption context**: "Frankfurt airport weather disruption" → real-time reports on runway closures, de-icing delays
- **ATC issues**: "Eurocontrol ATFM restrictions" → current flow management status
- **Airport events**: "Strikes at Munich airport" → labor action timing
- **Event-driven demand**: "Champions League final Frankfurt" → explains unusual load patterns
- **Regulatory changes**: "NOTAM Frankfurt runway" → real-time operational notices

### Google Maps Grounding
- **Crew positioning**: nearest available crew member's travel time to airport
- **Ground transport alternatives**: for disrupted passengers (train connections, bus routes)
- **Alternate airport routing**: distance/time to diversion airports
- **Airport surface navigation**: terminal distances, gate proximity for tight connections

---

## 9. Highest-Value Hackathon Use Cases

### Tier 1: Strongest Fit (API data + Grounding + clear pain point)

#### A. "Disruption Intelligence Briefing" Agent
**What**: When a disruption hits (detected via MQTT push), the agent automatically assembles a briefing: which flights are affected, estimated cascade impact, weather/ATC context (Search grounding), crew positioning options (Maps grounding), and recommended recovery actions ranked by cost.

**Why it works**: Combines ALL available tools. Solves the "controller opens 5 different screens" problem. Doesn't replace decisions — presents options with context.

**Demo-ability**: Show a real cancelled flight → agent pulls context → generates briefing → presents options. Very visual.

#### B. "Connection Protection Advisor"
**What**: Real-time agent monitoring all inbound flights to a hub. When delays propagate, it identifies endangered connections, evaluates hold-vs-rebook tradeoffs (factoring in EU261 exposure), and recommends which departures to hold and for how long.

**Why it works**: Uses flight status API (arrival estimates) + schedules (connections) + Search (delay context) + Maps (alternative routing for passengers). Directly addresses Frankfurt's MCT increase problem.

**Demo-ability**: Show a wave arriving at Frankfurt with mixed delays → agent identifies at-risk connections → recommends holds with cost/benefit.

#### C. "Network Ripple Predictor"
**What**: Agent monitors real-time disruption signals (MQTT) + weather forecasts (Search grounding) + ATC restrictions (Search grounding) and predicts which flights downstream will be affected before the cascade reaches them. Enables pre-positioning of recovery resources.

**Why it works**: Moves from reactive to predictive. Uses the 360-day schedule data to model downstream impact of current disruptions. Grounding adds "what's coming next" (weather front, ATC flow rate changes).

**Demo-ability**: Show weather approaching Frankfurt → agent predicts which of the next 2 waves will be affected → pre-positions recommendations.

### Tier 2: Good Fit (some data limitations but compelling story)

#### D. "Alternate Station Finder"
**What**: When a diversion or cancellation occurs, agent finds optimal alternate airports considering: distance (Maps), available LH flights from alternate (schedules API), ground transport for pax (Maps), weather at alternates (Search), and airport facilities.

#### E. "Cross-Group Recovery Advisor"
**What**: For a disrupted LH Group route, agent checks whether Swiss/Austrian/Brussels/Eurowings has capacity on similar routes — using public flight status to identify flights with potential availability.

---

## 10. Recommended Pitch Direction

**Lead with Use Case A ("Disruption Intelligence Briefing")** because:
1. It naturally combines all required tech (Lufthansa API + Gemini Grounding Search + Maps)
2. It solves a real, documented pain point (OCC information overload)
3. It's B2B internal tooling, not customer-facing
4. It augments humans with guardrails, doesn't replace them
5. It's highly demo-able within 24 hours
6. It tells a compelling story: "When a disruption hits, your OCC controller currently opens 5 systems, makes 12 phone calls, and spends 45 minutes assembling context. Our agent does it in 30 seconds."

**Backup with Use Case B ("Connection Protection Advisor")** as the focused, narrower version if A feels too broad.
