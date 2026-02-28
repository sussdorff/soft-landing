# DDD / Ports & Adapters Refactoring Plan

**Bead:** soft-landing-bah
**Team:** soft-landing-ddd-refactor
**Status:** In Progress
**Started:** 2026-02-28

## Goal

Transform the flat monolithic architecture into a Ports & Adapters (Hexagonal) architecture to enable:

1. **Parallel agent work** — Each adapter/port is independent, minimal merge conflicts
2. **Better testability** — Inject mock ports instead of mocking deep dependencies
3. **Clear boundaries** — Business logic isolated from infrastructure
4. **Easy to add adapters** — New external service? Create new adapter, don't touch business logic

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI (main.py)                        │
│  Dependency Injection: wire ports, adapters, repositories       │
└────────────────┬─────────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┬──────────────┐
    │            │            │              │              │
    ▼            ▼            ▼              ▼              ▼
┌─────────┐ ┌──────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐
│Ports    │ │Adapters  │ │Repositories │ │Services    │ │Business    │
│         │ │          │ │             │ │(wrapped)   │ │Logic       │
├─────────┤ ├──────────┤ ├─────────────┤ ├────────────┤ ├────────────┤
│FlightDP │◄─│LH API    │ │Disruption   │ │lufthansa   │ │Disruption  │
│Grounding│◄─│Gemini    │ │Passenger    │ │gemini      │ │Engine      │
│Notif    │◄─│Static    │ │Option       │ │            │ │            │
│Repo ×4  │◄─│WebSocket │ │Wish         │ │            │ │Option      │
└─────────┘ └──────────┘ └─────────────┘ └────────────┘ │Generator   │
                                                          └────────────┘
```

## Task Breakdown

### Phase 1: Foundation (Tasks 1-4) — Can Run in Parallel

| Task | Owner | Dependencies | Status |
|------|-------|--------------|--------|
| **#1** Define 7 Port interfaces | port-designer | None | 🔄 In Progress |
| **#2** StaticDataAdapter (offline fallback) | static-adapter-dev | #1 | ⏳ Blocked |
| **#3** LufthansaAPIAdapter (wrap LH client) | lh-adapter-dev | #1 | ⏳ Blocked |
| **#4** GeminiGroundingAdapter (wrap Gemini) | gemini-adapter-dev | #1 | ⏳ Blocked |

### Phase 2: Refactoring Services (Tasks 5-8) — Run After Phase 1

| Task | Owner | Dependencies | Status |
|------|-------|--------------|--------|
| **#5** Refactor store.py → Repositories | (pending) | #1 | ⏳ Blocked |
| **#6** Refactor OptionGenerator (inject ports) | (pending) | #1-5 | ⏳ Blocked |
| **#7** Refactor DisruptionEngine (inject ports) | (pending) | #1, #5 | ⏳ Blocked |
| **#8** WebSocketNotificationAdapter | (pending) | #1 | ⏳ Blocked |

### Phase 3: Integration & Testing (Tasks 9-11) — Final Phase

| Task | Owner | Dependencies | Status |
|------|-------|--------------|--------|
| **#9** Integrate in main.py + wire DI | (pending) | #6-8 | ⏳ Blocked |
| **#10** Write comprehensive tests | (pending) | #9 | ⏳ Blocked |
| **#11** Cleanup old files + finalize | (pending) | #10 | ⏳ Blocked |

## Current Architecture Problems

### 1. Tight Coupling
```python
# CURRENT (bad): Direct imports
class DisruptionEngine:
    def __init__(self, session):
        self.option_gen = OptionGenerator(gemini, lh_client)
        self.gemini = gemini
        self.ws = manager  # global

# DESIRED (good): Injected dependencies
class DisruptionEngine:
    def __init__(self, repositories, ports):
        self.option_gen = option_gen  # injected
```

### 2. Merge Conflicts
- Multiple agents edit `option_generator.py` (1168 lines) → conflicts
- Multiple agents edit `services/*.py` → conflicts
- **Solution:** Each adapter gets own file → parallel work, no conflicts

### 3. Hard to Test
- Can't mock Gemini without @patch decorators
- Can't test without PostgreSQL (need in-memory SQLite)
- **Solution:** Inject mock ports in tests, no decorators needed

### 4. Monolithic Option Generator
- 1168 lines mixing business logic + fallback data + API calls
- Hard to understand data flow
- **Solution:** Split into algorithm (OptionGenerator) + data sources (adapters)

## Port Definitions (Task #1)

### 1. FlightDataPort
```python
# Lufthansa API abstraction
async def get_schedules(origin, dest, date, *, direct_flights=False) -> dict
async def get_lounges(airport_code, *, tier_code=None, cabin_class=None) -> dict
async def get_flight_status(flight_number, date) -> dict
async def get_seat_map(flight_number, origin, dest, date, cabin) -> dict
async def get_airport_info(airport_code) -> dict
```

**Adapters:**
- `LufthansaAPIAdapter` — Production (wraps LufthansaClient with error handling)
- `StaticDataAdapter` — Offline fallback (hardcoded templates)

### 2. GroundingPort
```python
# Gemini + Google Search/Maps grounding
async def find_nearby_hotels(airport_code, max_results=5) -> list[HotelOption]
async def find_ground_transport(origin_airport, destination) -> list[TransportOption]
async def explain_disruption(disruption_type, reason, destination) -> str
async def get_flight_context(flight_number, origin, dest) -> FlightContext
async def describe_option(option_type, details) -> str
```

**Adapters:**
- `GeminiGroundingAdapter` — Production (wraps GeminiGroundingService)
- `StaticDataAdapter` — Offline fallback (empty/template returns)

### 3. NotificationPort
```python
# WebSocket real-time updates
async def send_to_passenger(passenger_id, event_type, data) -> None
async def send_to_dashboard(disruption_id, event_type, data) -> None
```

**Adapters:**
- `WebSocketNotificationAdapter` — Production (wraps ConnectionManager)

### 4-7. Repository Ports
```python
# Persistent storage abstraction
class DisruptionRepository
class PassengerRepository
class OptionRepository
class WishRepository
```

**Adapters:**
- Refactored `store.py` — PostgreSQL implementation

## File Changes Summary

### New Files (Created)
```
app/ports/                           # 7 ports, ~400 lines total
  __init__.py
  flight_data.py
  grounding.py
  notification.py
  repositories.py

app/adapters/                        # 5 adapters, ~500 lines total
  __init__.py
  static_data.py                     # Extracted from option_generator.py
  lufthansa_api.py                   # Wraps LufthansaClient
  gemini_grounding.py                # Wraps GeminiGroundingService
  websocket_notification.py          # Wraps ConnectionManager

tests/test_ports.py                  # Port contract tests
tests/test_adapters/                 # Adapter tests
```

### Modified Files
```
app/services/option_generator.py     # Remove static dicts, inject ports
app/services/disruption_engine.py    # Inject ports/repos, no direct DB
app/main.py                          # Wire all dependencies
app/store.py                         # Refactor into repository classes
                                     # OR: create app/repositories/
```

### Files Unchanged
```
app/models.py                        # Domain types (no changes)
app/db/engine.py                     # DB setup (no changes)
app/db/tables.py                     # ORM schema (no changes)
app/ws.py                            # WebSocket manager (wrapped by adapter)
app/services/lufthansa.py            # LH client (wrapped by adapter)
app/services/gemini.py               # Gemini service (wrapped by adapter)
```

## Development Workflow

### For Each Task

1. **Claim task:** `bd update <id> --status=in_progress`
2. **Work:** Implement files, write tests locally
3. **Test:** `uv run pytest tests/` to verify
4. **Commit:** `git commit -m "feat: <description>"` (not pushed yet)
5. **Mark done:** `bd close <id> --reason="..."`

### Pull Request (at end of refactoring)
After all tasks complete:
```bash
git pull --rebase
bd sync
git push
```

Then create PR from main → main with summary of all changes.

## Testing Strategy

### Unit Tests (Per Task)
- Port interfaces: Contract tests (all methods exist, proper signatures)
- Each adapter: Success cases + error cases
- Mocked dependencies (no HTTP, no DB)

### Integration Tests
- DisruptionEngine with mock repos/ports
- End-to-end: event → options → WebSocket notifications
- Use in-memory DB for speed

### Existing Tests
- Update `tests/test_disruption_engine.py` to use injected ports
- Existing tests should still pass with minimal changes

## Rollout Plan

1. **Implement tasks 1-11** (this document)
2. **Run full test suite** (`uv run pytest`)
3. **Manual testing** on dev environment (events + dashboard)
4. **Create PR** with all changes
5. **Code review** + merge
6. **Deploy** to production (CI/CD handles it)

## Success Criteria

- ✓ All 11 tasks completed
- ✓ Tests pass: `uv run pytest` → 100% green
- ✓ No regression: existing endpoints work the same
- ✓ Better architecture: clear separation of concerns
- ✓ Maintainability: new adapters can be added easily
- ✓ Testability: mock ports in unit tests, no @patch decorators
- ✓ Reduced merge conflicts: each adapter = independent file

## Next Steps

1. **Port-designer** continues with Task #1 (defining ports)
2. **Other agents** wait for Task #1, then work on Tasks 2-4 in parallel
3. **Check progress:** `bd ready` to see available work
4. **Weekly sync:** Review blockers and reassign work as needed

---

**Last Updated:** 2026-02-28
**Team Lead:** malte
**Slack:** #soft-landing (updates posted here)
