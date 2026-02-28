---
name: lufthansa-api
description: Query Lufthansa Open API for flight status, schedules, airport data, seat maps, and lounges. OAuth2 token management included. Triggers on lufthansa, lh api, flight status, flight schedule, seat map, airport info, lounges, lh flight.
triggers: lufthansa, lh api, flight status, flight schedule, seat map, airport, lounges, lh flight, flugstatus, fluege
---

# Lufthansa Open API

CLI access to Lufthansa Flight Ops, References, and Offers APIs via OAuth2 client credentials.

## When to Use

- Querying real-time flight status (single flight, route, airport departures/arrivals)
- Looking up flight schedules between airports
- Fetching airport reference data (info, nearest airports)
- Getting seat maps for specific flights
- Finding lounge information at airports
- Looking up airline, country, city, aircraft reference data
- Any task involving Lufthansa flight operations data

## Do NOT

- Do NOT use Cargo or Partner/Fares endpoints (HTTP 596 — no access)
- Do NOT hardcode tokens — always fetch fresh via OAuth2
- Do NOT exceed rate limits (tokens last 36h but API rate-limits aggressively, reuse tokens)
- Do NOT use the old token after "Account Inactive" — get a fresh one

## Credentials

Stored in project `.env` files. For the SoftLanding project:

```
LH_API_CLIENT_ID=u4bnhm9uhcmq5yjt588sarh7
LH_API_CLIENT_SECRET=TYCf4nYDvfwc9StPyBnk
```

Alt credentials (backup):
```
LH_API_CLIENT_ID=74ypmwy4bdsaxx2c6hjc66jbj
LH_API_CLIENT_SECRET=9y3upVx3We
```

## OAuth2 Token

```bash
# Get token (valid ~36 hours)
TOKEN=$(/usr/bin/curl -s -X POST "https://api.lufthansa.com/v1/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=CLIENT_ID&client_secret=CLIENT_SECRET&grant_type=client_credentials" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Or use the helper script:
```bash
TOKEN=$(bash ~/.claude/skills/lufthansa-api/scripts/get-token.sh)
```

## Available Endpoints

### Operations (Flight Data)

| Endpoint | Path | Description |
|----------|------|-------------|
| Flight Status | `/operations/flightstatus/{flightNumber}/{date}` | Single flight status |
| Status by Route | `/operations/flightstatus/route/{origin}/{dest}/{date}` | All flights on a route |
| Departures | `/operations/flightstatus/departures/{airport}/{datetime}` | All departures from airport |
| Arrivals | `/operations/flightstatus/arrivals/{airport}/{datetime}` | All arrivals at airport |
| Customer Flight Info | `/operations/customerflightinformation/{flightNumber}/{date}` | Passenger-facing flight info |
| Schedules | `/operations/schedules/{origin}/{dest}/{date}` | Flight schedules between airports |

### References (Static Data)

| Endpoint | Path | Description |
|----------|------|-------------|
| Airports | `/mds-references/airports/{code}?lang=EN` | Airport info (name, coords, timezone) |
| Nearest Airports | `/mds-references/airports/nearest/{lat},{lon}?lang=EN` | Up to 5 nearest airports |
| Airlines | `/mds-references/airlines/{code}` | Airline info |
| Countries | `/mds-references/countries/{code}?lang=EN` | Country info |
| Cities | `/mds-references/cities/{code}?lang=EN` | City info |
| Aircraft | `/mds-references/aircraft` or `/mds-references/aircraft/{code}` | Aircraft types (code format: 3-char, e.g. "33P") |

### Offers

| Endpoint | Path | Description |
|----------|------|-------------|
| Seat Maps | `/offers/seatmaps/{flight}/{origin}/{dest}/{date}/{cabin}` | Seat availability (cabin: F/C/M/Y) |
| Lounges | `/offers/lounges/{airport}` | Lounge info (optional: ?cabinClass=F or ?tierCode=SEN) |

### NOT Available (596)

| Endpoint | Reason |
|----------|--------|
| Cargo Tracking | No API access |
| Best Prices / Fares | Partner API — not included |

## Common Queries

### Flight Status

```bash
# LH400 today
/usr/bin/curl -s "https://api.lufthansa.com/v1/operations/flightstatus/LH400/2026-02-28" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json" | python3 -m json.tool
```

**Response structure:**
```
FlightStatusResource.Flights.Flight[] -> {
  Departure: { AirportCode, ScheduledTimeLocal, ActualTimeLocal, TimeStatus{Code,Definition}, Terminal{Name,Gate} }
  Arrival: { AirportCode, ScheduledTimeLocal, EstimatedTimeLocal, TimeStatus{Code,Definition}, Terminal{Name} }
  MarketingCarrier: { AirlineID, FlightNumber }
  OperatingCarrier: { AirlineID, FlightNumber }
  Equipment: { AircraftCode, AircraftRegistration }
  FlightStatus: { Code, Definition }  // DP=Departed, LD=Landed, CD=Cancelled, etc.
  ServiceType: "Passenger"
}
```

**TimeStatus codes:** DL=Delayed, OT=On Time, NO=No data, NI=Not set
**FlightStatus codes:** DP=Departed, LD=Landed, CD=Cancelled, DL=Delayed, NA=Not Available

### Departures from Airport

```bash
# All departures from FRA in a time window
/usr/bin/curl -s "https://api.lufthansa.com/v1/operations/flightstatus/departures/FRA/2026-02-28T08:00" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json"
```

Note: Only one datetime parameter (start). API returns ~4 hours of data.

### Schedules

```bash
# FRA to JFK on a date (add ?directFlights=1 for non-stop only)
/usr/bin/curl -s "https://api.lufthansa.com/v1/operations/schedules/FRA/JFK/2026-02-28" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json"
```

### Airport Info

```bash
/usr/bin/curl -s "https://api.lufthansa.com/v1/mds-references/airports/FRA?lang=EN" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json"
```

**Response:** `AirportResource.Airports.Airport -> { AirportCode, Position{Coordinate{Latitude,Longitude}}, CityCode, CountryCode, Names, UtcOffset, TimeZoneId }`

### Nearest Airports

```bash
# 3 decimal precision for coordinates
/usr/bin/curl -s "https://api.lufthansa.com/v1/mds-references/airports/nearest/50.033,8.571?lang=EN" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json"
```

Returns up to 5 airports sorted by distance (in KM).

### Seat Map

```bash
/usr/bin/curl -s "https://api.lufthansa.com/v1/offers/seatmaps/LH400/FRA/JFK/2026-02-28/M" \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/json"
```

Cabin class: F=First, C=Business, M=Economy, Y=Economy (alias)

## Parameter Formats

| Parameter | Format | Example |
|-----------|--------|---------|
| flightNumber | IATA carrier + number | `LH400`, `LH2037` |
| date | yyyy-MM-dd | `2026-02-28` |
| datetime | yyyy-MM-ddTHH:mm | `2026-02-28T08:00` |
| airport | 3-letter IATA | `FRA`, `JFK`, `MUC` |
| coordinates | lat,lon (3 decimals) | `50.033,8.571` |
| lang | 2-letter ISO 639-1 | `EN`, `DE` |
| cabinClass | single letter | `F`, `C`, `M`, `Y` |

## Python Client

The SoftLanding backend has an async client at `backend/app/services/lufthansa.py`:

```python
from app.services.lufthansa import LufthansaClient

async with LufthansaClient() as lh:
    status = await lh.get_flight_status("LH400", "2026-02-28")
    schedules = await lh.get_schedules("FRA", "JFK", "2026-02-28", direct_flights=True)
    airport = await lh.get_airport_info("FRA", lang="DE")
    nearest = await lh.get_nearest_airports(50.033, 8.571)
    seatmap = await lh.get_seat_map("LH400", "FRA", "JFK", "2026-02-28", "M")
    lounges = await lh.get_lounges("FRA", cabin_class="C")
```

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Parse response |
| 401 | Token expired | Re-authenticate |
| 404 | Not found | Check parameter format |
| 429 | Rate limited | Back off exponentially |
| 500-504 | Server error | Retry with backoff |
| 596 | No API access | Endpoint not available for these credentials |
