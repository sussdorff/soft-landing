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
- **Model:** Gemini (organizer referenced "Gemini 3" — likely Gemini 2.0 Flash / Pro or next-gen)
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

---

## Stack Ideas (not confirmed)

| Layer | Options |
|-------|---------|
| LLM | Gemini 2.0 Pro / Flash (with Grounding enabled) |
| Backend | Python (LangChain/LangGraph) or TypeScript |
| Frontend | Next.js or lightweight Streamlit for demo |
| Data | Lufthansa Flight Ops API + GDS APIs (if accessible) |
| Grounding | Google Search + Google Maps via Gemini Grounding API |
