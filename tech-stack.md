# Tech Stack — Innovate the Skies & Beyond

> Sourced from organizer hints in Discord (Alex), 2026-02-27

---

## Allowed / Encouraged Tools

### Lufthansa Flight Ops API
- **Docs:** https://developer.lufthansa.com/docs/read/api_flightops
- Internal flight operations data — not just public flight status
- Organizer explicitly encouraged use of this API
- Relevant for ideas around internal airline ops, standby routing, crew tooling, etc.

### Google Gemini (with Grounding)
- **Model:** Gemini 3.0
- Grounding is a key differentiator the jury wants to see used

#### Grounding with Google Search
- **Docs:** https://ai.google.dev/gemini-api/docs/google-search
- Grounds model responses in real-time Google Search results
- Improves factual accuracy, adds citations
- Use case: real-time flight disruption news, destination event data, weather context

#### Grounding with Google Maps
- **Docs:** https://ai.google.dev/gemini-api/docs/maps-grounding
- Grounds responses in real-world location data from Google Maps
- Use case: airport proximity, destination suitability, route visualization

---

## What the Jury Likely Values

Based on organizer hints:
1. **Uses Lufthansa Flight Ops API** — not just public data
2. **Grounding in Gemini** — real-time, factually accurate, cited responses
3. **Solves an internal / operational pain point** — not another consumer price comparison
4. **Novel angle** — employees, crews, ops, not end-customer booking

### Pitch Framing

Lead with the **gate agent dashboard** as the primary product. The story: "A single gate agent can handle 200 disrupted passengers in minutes instead of hours." The passenger app is the data collection mechanism that *feeds* the operational tool — supporting infrastructure, not the headline. This positions Soft Landing as an **operational tool** (what the jury wants) rather than a consumer app.

---

## Stack Decisions

| Layer | Choice | Notes |
|-------|--------|-------|
| LLM | Gemini 3.0 (with Grounding enabled) | |
| Backend | **Python 3.14** | Gemini SDK, agent orchestration |
| Passenger App | **Kotlin Multiplatform (KMP)** | Targets: Android, iOS, Web. Compiles to native binaries (no runtime layer like Flutter). Can interop with Swift code on iOS. |
| Gate Agent Dashboard | **React** (web) | WebSocket-based for real-time notifications. Reference: Mira project for WS setup. |
| Real-time | **WebSockets** | Critical for gate agent dashboard — live updates as passenger wishes stream in |
| Data | Lufthansa Flight Ops API + GDS APIs (if accessible) | |
| Grounding | Google Search + Google Maps via Gemini Grounding API | |

### Why KMP over Flutter

- KMP compiles to **native binaries** — on iOS it's indistinguishable from a native app
- Flutter has a rendering middle layer; KMP does not
- KMP can interop with existing Swift code — you can implement Swift-native patterns in Kotlin
- Compose Multiplatform for shared UI across Android/iOS/Web
