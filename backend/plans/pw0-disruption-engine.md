# Plan: Disruption Engine — Event Detection & Classification

**Bead**: soft-landing-pw0
**Status**: Ready to implement

## Context

The backend already has:
- FastAPI scaffolding with SQLAlchemy async (tables, store, models)
- Pydantic models: `Disruption`, `Passenger`, `Option`, `Wish` etc.
- Two seed scenarios (snowstorm, diversion) that directly insert DB rows
- `POST /disruptions/simulate` endpoint that drops DB and re-seeds
- `LufthansaClient` service (Flight Ops API: flight status, schedules, seat maps)
- `GeminiGroundingService` (explain disruption, find transport/hotels, flight context)
- WebSocket connection manager for passenger + dashboard channels

What's missing: a **Disruption Engine** module that:
1. Receives disruption events (currently via simulate endpoint, later MQTT)
2. Classifies them (cancellation, diversion, delay, gate change)
3. Determines affected passengers
4. Triggers the option generation pipeline (which feeds into the existing store)
5. Sends real-time notifications via WebSocket

## Developer Decisions

1. **No real MQTT yet** — the hackathon uses the simulate endpoint. The engine provides an `ingest_event()` async method that the simulate endpoint calls. MQTT wiring is deferred.
2. **Classification logic** — use a simple rule-based classifier (pattern matching on LH API status codes / reason strings). No ML. DisruptionType enum already exists: CANCELLATION, DIVERSION, DELAY. Add GATE_CHANGE.
3. **Passenger lookup** — affected passengers determined by flight number match against their original itinerary segments in DB.
4. **Option generation** — the engine calls a new `OptionGeneratorService` that wraps the existing Gemini + LH API services. For the hackathon, we also keep the seed-based option generation as a fast fallback when API keys aren't configured.
5. **Hub disruption handling** — multiple flights → multiple disruption records, each with its own passenger set. The simulate endpoint already handles this via seeds.
6. **WebSocket push** — after creating a disruption + options, push `disruption_created` to dashboard and `disruption_notification` + `options_ready` to each affected passenger.
7. **DB schema** — no changes to existing tables needed. The engine uses the existing store functions.
8. **Testing** — use pytest with async fixtures and an in-memory SQLite DB (aiosqlite) for unit tests. Mock Gemini/LH API calls.

## Test Plan

**Framework**: pytest (with pytest-asyncio)
**Dependencies needed**: pytest, pytest-asyncio, aiosqlite (dev deps only)

### Unit Tests
1. `test_classify_event` — verify classification of raw event dicts into DisruptionType
2. `test_determine_affected_passengers` — given passengers with itinerary segments, find those on the affected flight
3. `test_ingest_event_creates_disruption` — end-to-end: ingest raw event → disruption + passengers + options created in DB
4. `test_ingest_event_sends_websocket` — verify WS messages sent after ingestion
5. `test_gate_change_classification` — verify GATE_CHANGE type added and classified correctly
6. `test_hub_disruption_multiple_flights` — verify multiple flights create individual disruption records

## Step by Step Tasks

### Task 1: Add GATE_CHANGE to DisruptionType enum
- File: `backend/app/models.py`
- Add `GATE_CHANGE = auto()` to `DisruptionType`
- Non-TDD (enum addition)

### Task 2: Create DisruptionEngine service
- File: `backend/app/services/disruption_engine.py`
- Class `DisruptionEngine` with:
  - `__init__(self, session_factory, ws_manager)` — takes async session factory + WS manager
  - `classify_event(raw: dict) -> DisruptionType` — static/classmethod, rule-based classification
  - `find_affected_passengers(session, flight_number) -> list[PassengerRow]` — query segments table
  - `ingest_event(raw: dict) -> Disruption` — orchestrator: classify → create disruption → find pax → link pax → generate options → notify via WS
- TDD: write tests first for classify_event, find_affected_passengers, then ingest_event

### Task 3: Create OptionGeneratorService (stub/seed-based)
- File: `backend/app/services/option_generator.py`
- Class `OptionGeneratorService` with:
  - `generate_options(session, disruption, passenger) -> list[OptionRow]` — creates options based on disruption type + destination
  - For hackathon: use seed-style deterministic option generation (rebook, hotel, ground, alt_airport) based on destination lookup tables
  - Later: wire in Gemini + LH API for live option generation
- TDD: test that options are created for a passenger given a disruption

### Task 4: Wire DisruptionEngine into simulate endpoint
- File: `backend/app/main.py`
- Modify `POST /disruptions/simulate` to use `DisruptionEngine.ingest_event()` instead of direct seed calls
- Keep seed scenarios as data sources but route through the engine for classification + WS notifications
- Keep backward compatibility: existing seed scenarios still produce the same data

### Task 5: Add new endpoint POST /disruptions/ingest
- File: `backend/app/main.py`
- New endpoint that accepts a raw disruption event JSON (simulating what MQTT would deliver)
- Calls `DisruptionEngine.ingest_event()`
- Returns the created Disruption

### Task 6: Write unit tests
- File: `backend/tests/test_disruption_engine.py`
- Tests per test plan above
- Use aiosqlite for in-memory DB
- Mock WebSocket manager

### Task 7: Lint and verify
- Run ruff check on all changed files
- Run pytest
- Verify all tests pass

## Recommendation

**Ready to implement**
