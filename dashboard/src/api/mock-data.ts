import type {
  Disruption,
  Passenger,
  Option,
  Wish,
  PassengerProfile,
} from "../types";

// ============================================================
// Mock Data — Multiple flights at Munich during snowstorm
// ============================================================

export const DISRUPTIONS: Disruption[] = [
  {
    id: "dis-001",
    type: "delay",
    flightNumber: "LH1234",
    origin: "MUC",
    destination: "CDG",
    reason: "Heavy snowfall in Munich — departures delayed due to runway clearing",
    explanation:
      "Due to heavy snowfall across southern Bavaria, Munich Airport is experiencing delays while runways are being cleared. Your flight LH1234 MUC→CDG, originally scheduled for 15:30, is now delayed by 30 minutes to 16:00. Some connecting passengers may be affected. We're monitoring the situation and working to get everyone to their destination.",
    detectedAt: "2026-03-01T14:30:00Z",
    affectedPassengerIds: ["pax-001","pax-002","pax-003","pax-004","pax-005","pax-006","pax-007","pax-008","pax-009","pax-010","pax-011","pax-012"],
  },
  {
    id: "dis-002",
    type: "cancellation",
    flightNumber: "LH2030",
    origin: "MUC",
    destination: "LHR",
    reason: "Aircraft technical issue — hydraulic system fault detected during pre-flight",
    explanation:
      "Flight LH2030 MUC→LHR has been cancelled due to a hydraulic system fault detected during pre-flight checks. No replacement aircraft is currently available at Munich. We are working on alternative routing for all affected passengers.",
    detectedAt: "2026-03-01T13:45:00Z",
    affectedPassengerIds: ["pax-200","pax-201","pax-202","pax-203","pax-204","pax-205","pax-206","pax-207"],
  },
  {
    id: "dis-003",
    type: "delay",
    flightNumber: "LH1830",
    origin: "MUC",
    destination: "FRA",
    reason: "Crew rotation delay — inbound crew arriving late from Berlin",
    explanation:
      "Flight LH1830 MUC→FRA is delayed by approximately 45 minutes due to the late arrival of the operating crew from Berlin. New estimated departure 16:45 (originally 16:00). Passengers with tight connections at Frankfurt may need rebooking.",
    detectedAt: "2026-03-01T15:00:00Z",
    affectedPassengerIds: ["pax-100","pax-106","pax-110","pax-114","pax-120","pax-126"],
  },
];

// ---- Passengers per disruption ----

const PASSENGERS_DIS001: Passenger[] = [
  { id: "pax-001", name: "Elena Vasquez", bookingRef: "LH7KQ2", originalItinerary: { segments: [{ flightNumber: "LH1820", origin: "BCN", destination: "MUC", departure: "2026-03-01T10:15:00Z", arrival: "2026-03-01T12:40:00Z" }, { flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "denied", denialCount: 2, priority: 2 },
  { id: "pax-002", name: "Marcus Chen", bookingRef: "LH3NP8", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "denied", denialCount: 1, priority: 1 },
  { id: "pax-003", name: "Aisha Okafor", bookingRef: "LH9WM4", originalItinerary: { segments: [{ flightNumber: "LH340", origin: "LOS", destination: "MUC", departure: "2026-03-01T06:00:00Z", arrival: "2026-03-01T12:30:00Z" }, { flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }, { flightNumber: "AF1680", origin: "CDG", destination: "ABJ", departure: "2026-03-01T20:00:00Z", arrival: "2026-03-02T00:30:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
  { id: "pax-004", name: "Thomas Bergmann", bookingRef: "LH2JT6", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
  { id: "pax-005", name: "Yuki Tanaka", bookingRef: "LH5RX1", originalItinerary: { segments: [{ flightNumber: "LH715", origin: "NRT", destination: "MUC", departure: "2026-02-28T22:00:00Z", arrival: "2026-03-01T06:30:00Z" }, { flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
  { id: "pax-006", name: "Sophie Dubois", bookingRef: "LH8FK3", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-007", name: "Raj Patel", bookingRef: "LH4BN9", originalItinerary: { segments: [{ flightNumber: "LH760", origin: "DEL", destination: "MUC", departure: "2026-03-01T02:00:00Z", arrival: "2026-03-01T07:30:00Z" }, { flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-008", name: "Anna Kowalski", bookingRef: "LH6GT5", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }, { flightNumber: "AF990", origin: "CDG", destination: "JFK", departure: "2026-03-01T19:45:00Z", arrival: "2026-03-01T22:30:00Z" }] }, status: "approved", denialCount: 0, priority: 0 },
  { id: "pax-009", name: "Carlos Rivera", bookingRef: "LH1DM7", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-010", name: "Ingrid Müller", bookingRef: "LH7YC2", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
  { id: "pax-011", name: "David Kim", bookingRef: "LH3PA8", originalItinerary: { segments: [{ flightNumber: "LH492", origin: "ICN", destination: "MUC", departure: "2026-02-28T21:00:00Z", arrival: "2026-03-01T05:00:00Z" }, { flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }, { flightNumber: "AF1380", origin: "CDG", destination: "LYS", departure: "2026-03-01T19:00:00Z", arrival: "2026-03-01T20:10:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-012", name: "Fatima Al-Rashid", bookingRef: "LH9KE4", originalItinerary: { segments: [{ flightNumber: "LH1234", origin: "MUC", destination: "CDG", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T17:15:00Z" }] }, status: "approved", denialCount: 1, priority: 0 },
];

const PASSENGERS_DIS002: Passenger[] = [
  { id: "pax-200", name: "James Whitfield", bookingRef: "LH4KR1", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-201", name: "Charlotte Beaumont", bookingRef: "LH8WQ5", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }, { flightNumber: "BA306", origin: "LHR", destination: "EDI", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-01T19:00:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
  { id: "pax-202", name: "Oliver Hastings", bookingRef: "LH2NM3", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-203", name: "Priya Sharma", bookingRef: "LH6VC8", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }, { flightNumber: "BA117", origin: "LHR", destination: "JFK", departure: "2026-03-01T18:00:00Z", arrival: "2026-03-01T21:00:00Z" }] }, status: "denied", denialCount: 1, priority: 1 },
  { id: "pax-204", name: "William Clarke", bookingRef: "LH1DT6", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }] }, status: "approved", denialCount: 0, priority: 0 },
  { id: "pax-205", name: "Sarah Mitchell", bookingRef: "LH9PJ4", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-206", name: "George Adebayo", bookingRef: "LH3FZ7", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }, { flightNumber: "BA73", origin: "LHR", destination: "LOS", departure: "2026-03-01T21:00:00Z", arrival: "2026-03-02T05:30:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-207", name: "Emma Thompson", bookingRef: "LH5BX2", originalItinerary: { segments: [{ flightNumber: "LH2030", origin: "MUC", destination: "LHR", departure: "2026-03-01T14:15:00Z", arrival: "2026-03-01T15:45:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
];

const PASSENGERS_DIS003: Passenger[] = [
  { id: "pax-100", name: "Pierre Laurent", bookingRef: "LH2AX9", originalItinerary: { segments: [{ flightNumber: "LH1830", origin: "MUC", destination: "FRA", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-01T17:05:00Z" }] }, status: "unaffected", denialCount: 0, priority: 0 },
  { id: "pax-106", name: "Ahmed Hassan", bookingRef: "LH7NJ4", originalItinerary: { segments: [{ flightNumber: "LH1830", origin: "MUC", destination: "FRA", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-01T17:05:00Z" }, { flightNumber: "LH340", origin: "FRA", destination: "CAI", departure: "2026-03-01T19:30:00Z", arrival: "2026-03-01T23:45:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-110", name: "Henrik Larsen", bookingRef: "LH4UT3", originalItinerary: { segments: [{ flightNumber: "LH1830", origin: "MUC", destination: "FRA", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-01T17:05:00Z" }, { flightNumber: "LH902", origin: "FRA", destination: "IAD", departure: "2026-03-01T18:30:00Z", arrival: "2026-03-01T22:00:00Z" }] }, status: "chose", denialCount: 0, priority: 0 },
  { id: "pax-114", name: "Kenji Nakamura", bookingRef: "LH9CM2", originalItinerary: { segments: [{ flightNumber: "LH1830", origin: "MUC", destination: "FRA", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-01T17:05:00Z" }, { flightNumber: "LH710", origin: "FRA", destination: "NRT", departure: "2026-03-01T20:15:00Z", arrival: "2026-03-02T15:30:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-120", name: "Andrei Volkov", bookingRef: "LH8SA1", originalItinerary: { segments: [{ flightNumber: "LH1830", origin: "MUC", destination: "FRA", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-01T17:05:00Z" }, { flightNumber: "LH450", origin: "FRA", destination: "ORD", departure: "2026-03-01T19:00:00Z", arrival: "2026-03-01T22:15:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
  { id: "pax-126", name: "Jan Kříž", bookingRef: "LH2OA8", originalItinerary: { segments: [{ flightNumber: "LH1830", origin: "MUC", destination: "FRA", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-01T17:05:00Z" }, { flightNumber: "LH760", origin: "FRA", destination: "DEL", departure: "2026-03-01T21:00:00Z", arrival: "2026-03-02T08:30:00Z" }] }, status: "notified", denialCount: 0, priority: 0 },
];

export const PASSENGERS_MAP: Record<string, Passenger[]> = {
  "dis-001": PASSENGERS_DIS001,
  "dis-002": PASSENGERS_DIS002,
  "dis-003": PASSENGERS_DIS003,
};

// ---- Options per disruption ----

const OPTIONS_DIS001: Record<string, Option[]> = {
  "pax-001": [
    { id: "opt-001a", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train from Munich Hauptbahnhof. Arrives late evening.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
    { id: "opt-001b", type: "hotel", summary: "Hilton Munich Airport + morning flight LH1238", description: "Overnight at airport hotel, first flight tomorrow 07:15.", details: { hotelName: "Hilton Munich Airport", address: "Terminalstr. Mitte 20, 85356 Munich", location: { lat: 48.353, lng: 11.786 }, nextFlightNumber: "LH1238", nextFlightDeparture: "2026-03-02T07:15:00Z" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-001c", type: "alt_airport", summary: "Fly via FRA: LH110 MUC→FRA, LH1054 FRA→CDG", description: "Route via Frankfurt if FRA departures resume.", details: { viaAirport: "FRA", connectingFlight: "LH1054", transferMode: "train" as const, totalArrival: "2026-03-01T22:45:00Z" }, available: false, estimatedArrival: "2026-03-01T22:45:00Z" },
  ],
  "pax-002": [
    { id: "opt-002a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 22C", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "22C" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-002b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
    { id: "opt-002c", type: "hotel", summary: "NH Munich Airport + morning flight LH1238", description: "Overnight stay near airport, seat reserved on tomorrow's first flight.", details: { hotelName: "NH Munich Airport", address: "Lohstraße 21, 85445 Oberding", location: { lat: 48.345, lng: 11.802 }, nextFlightNumber: "LH1238", nextFlightDeparture: "2026-03-02T07:15:00Z" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
  ],
  "pax-003": [
    { id: "opt-003a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 14A", description: "Connect to AF1680 CDG→ABJ rebooked to tomorrow afternoon.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "14A" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-003b", type: "alt_airport", summary: "Via FRA: LH110 → LH562 FRA→ABJ direct", description: "Skip Paris entirely, fly direct FRA→ABJ if Frankfurt opens.", details: { viaAirport: "FRA", connectingFlight: "LH562", transferMode: "train" as const, totalArrival: "2026-03-02T05:30:00Z" }, available: true, estimatedArrival: "2026-03-02T05:30:00Z" },
  ],
  "pax-004": [
    { id: "opt-004a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 18F", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "18F" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-004b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
    { id: "opt-004c", type: "hotel", summary: "Hilton Munich Airport + morning flight LH1238", description: "Overnight at airport hotel, first flight tomorrow 07:15.", details: { hotelName: "Hilton Munich Airport", address: "Terminalstr. Mitte 20, 85356 Munich", location: { lat: 48.353, lng: 11.786 }, nextFlightNumber: "LH1238", nextFlightDeparture: "2026-03-02T07:15:00Z" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
  ],
  "pax-005": [
    { id: "opt-005a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 9B", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "9B" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-005b", type: "hotel", summary: "NH Munich Airport + morning flight LH1238", description: "Overnight stay near airport, seat reserved on tomorrow's first flight.", details: { hotelName: "NH Munich Airport", address: "Lohstraße 21, 85445 Oberding", location: { lat: 48.345, lng: 11.802 }, nextFlightNumber: "LH1238", nextFlightDeparture: "2026-03-02T07:15:00Z" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
  ],
  "pax-006": [
    { id: "opt-006a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 20A", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "20A" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-006b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
    { id: "opt-006c", type: "hotel", summary: "Hilton Munich Airport + morning flight LH1238", description: "Overnight at airport hotel, first flight tomorrow 07:15.", details: { hotelName: "Hilton Munich Airport", address: "Terminalstr. Mitte 20, 85356 Munich", location: { lat: 48.353, lng: 11.786 }, nextFlightNumber: "LH1238", nextFlightDeparture: "2026-03-02T07:15:00Z" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
  ],
  "pax-007": [
    { id: "opt-007a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 11D", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "11D" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-007b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
  ],
  "pax-008": [
    { id: "opt-008a", type: "rebook", summary: "LH1238 MUC→CDG + AF990 CDG→JFK, tomorrow", description: "Full rebooking: morning flight to CDG, evening connection to JFK.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "12A" }, available: true, estimatedArrival: "2026-03-02T22:30:00Z" },
    { id: "opt-008b", type: "alt_airport", summary: "Via FRA: LH110 MUC→FRA, LH400 FRA→JFK direct", description: "Skip Paris, fly direct to JFK from Frankfurt.", details: { viaAirport: "FRA", connectingFlight: "LH400", transferMode: "train" as const, totalArrival: "2026-03-02T04:00:00Z" }, available: false, estimatedArrival: "2026-03-02T04:00:00Z" },
  ],
  "pax-009": [
    { id: "opt-009a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 24E", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "24E" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-009b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
    { id: "opt-009c", type: "hotel", summary: "NH Munich Airport + morning flight LH1238", description: "Overnight stay near airport, seat reserved on tomorrow's first flight.", details: { hotelName: "NH Munich Airport", address: "Lohstraße 21, 85445 Oberding", location: { lat: 48.345, lng: 11.802 }, nextFlightNumber: "LH1238", nextFlightDeparture: "2026-03-02T07:15:00Z" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
  ],
  "pax-010": [
    { id: "opt-010a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 16C", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "16C" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-010b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
  ],
  "pax-011": [
    { id: "opt-011a", type: "rebook", summary: "LH1238 MUC→CDG + AF1380 CDG→LYS, tomorrow", description: "Full rebooking via CDG to Lyon. Arrives tomorrow afternoon.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "7A" }, available: true, estimatedArrival: "2026-03-02T12:10:00Z" },
    { id: "opt-011b", type: "ground", summary: "ICE + TGV: MUC → Lyon Part-Dieu direct", description: "Train via Stuttgart and Lyon. Long but arrives today.", details: { mode: "train" as const, route: "MUC Hbf → Stuttgart → Lyon Part-Dieu", departure: "2026-03-01T16:00:00Z", arrival: "2026-03-02T01:30:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T01:30:00Z" },
    { id: "opt-011c", type: "alt_airport", summary: "Via FRA: LH110 → AF7712 FRA→LYS", description: "Route via Frankfurt to Lyon, skipping CDG entirely.", details: { viaAirport: "FRA", connectingFlight: "AF7712", transferMode: "train" as const, totalArrival: "2026-03-01T23:00:00Z" }, available: true, estimatedArrival: "2026-03-01T23:00:00Z" },
  ],
  "pax-012": [
    { id: "opt-012a", type: "rebook", summary: "LH1238 MUC→CDG tomorrow 07:15, seat 5F", description: "First available direct flight tomorrow morning.", details: { flightNumber: "LH1238", origin: "MUC", destination: "CDG", departure: "2026-03-02T07:15:00Z", seatAvailable: "5F" }, available: true, estimatedArrival: "2026-03-02T09:00:00Z" },
    { id: "opt-012b", type: "ground", summary: "ICE train MUC → Paris Gare de l'Est", description: "Direct high-speed train, arrives late evening today.", details: { mode: "train" as const, route: "MUC Hbf → Paris Gare de l'Est", departure: "2026-03-01T17:30:00Z", arrival: "2026-03-02T00:15:00Z", provider: "Deutsche Bahn / SNCF" }, available: true, estimatedArrival: "2026-03-02T00:15:00Z" },
  ],
};

const OPTIONS_DIS002: Record<string, Option[]> = {
  "pax-200": [
    { id: "opt-200a", type: "rebook", summary: "LH2032 MUC→LHR 18:30, seat 8A", description: "Next direct flight to London this evening.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "8A" }, available: true, estimatedArrival: "2026-03-01T20:00:00Z" },
    { id: "opt-200b", type: "alt_airport", summary: "Via FRA: LH110 MUC→FRA, LH920 FRA→LHR", description: "Route via Frankfurt hub.", details: { viaAirport: "FRA", connectingFlight: "LH920", transferMode: "train" as const, totalArrival: "2026-03-01T21:30:00Z" }, available: true, estimatedArrival: "2026-03-01T21:30:00Z" },
  ],
  "pax-201": [
    { id: "opt-201a", type: "rebook", summary: "LH2032 MUC→LHR 18:30 + BA308 LHR→EDI", description: "Rebook to evening LHR flight, connect to Edinburgh.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "12C" }, available: true, estimatedArrival: "2026-03-02T00:00:00Z" },
    { id: "opt-201b", type: "alt_airport", summary: "LH940 MUC→EDI direct tomorrow 09:00", description: "Direct flight to Edinburgh tomorrow morning.", details: { viaAirport: "EDI", connectingFlight: "LH940", transferMode: "train" as const, totalArrival: "2026-03-02T10:30:00Z" }, available: true, estimatedArrival: "2026-03-02T10:30:00Z" },
  ],
  "pax-202": [
    { id: "opt-202a", type: "rebook", summary: "LH2032 MUC→LHR 18:30, seat 15D", description: "Next direct flight to London this evening.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "15D" }, available: true, estimatedArrival: "2026-03-01T20:00:00Z" },
    { id: "opt-202b", type: "ground", summary: "Train MUC→ZRH + SWISS LX318 ZRH→LHR", description: "Train to Zurich, then SWISS flight to London.", details: { mode: "train" as const, route: "MUC Hbf → Zürich HB", departure: "2026-03-01T15:30:00Z", arrival: "2026-03-01T19:30:00Z", provider: "Deutsche Bahn / SBB" }, available: true, estimatedArrival: "2026-03-01T23:00:00Z" },
  ],
  "pax-203": [
    { id: "opt-203a", type: "rebook", summary: "LH2032 MUC→LHR 18:30 + BA117 LHR→JFK", description: "Rebook to evening LHR flight, connect to JFK.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "3A" }, available: true, estimatedArrival: "2026-03-02T01:00:00Z" },
    { id: "opt-203b", type: "alt_airport", summary: "LH400 FRA→JFK direct via Frankfurt", description: "Train to Frankfurt, direct flight to JFK.", details: { viaAirport: "FRA", connectingFlight: "LH400", transferMode: "train" as const, totalArrival: "2026-03-02T04:00:00Z" }, available: true, estimatedArrival: "2026-03-02T04:00:00Z" },
  ],
  "pax-204": [
    { id: "opt-204a", type: "rebook", summary: "LH2032 MUC→LHR 18:30, seat 22B", description: "Next direct flight to London this evening.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "22B" }, available: true, estimatedArrival: "2026-03-01T20:00:00Z" },
  ],
  "pax-205": [
    { id: "opt-205a", type: "rebook", summary: "LH2032 MUC→LHR 18:30, seat 19E", description: "Next direct flight to London this evening.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "19E" }, available: true, estimatedArrival: "2026-03-01T20:00:00Z" },
    { id: "opt-205b", type: "hotel", summary: "Marriott MUC + LH2030 tomorrow 14:15", description: "Hotel overnight, same flight tomorrow.", details: { hotelName: "Marriott Munich Airport", address: "Alois-Steinecker-Str. 20", location: { lat: 48.349, lng: 11.790 }, nextFlightNumber: "LH2030", nextFlightDeparture: "2026-03-02T14:15:00Z" }, available: true, estimatedArrival: "2026-03-02T15:45:00Z" },
  ],
  "pax-206": [
    { id: "opt-206a", type: "rebook", summary: "LH2032 MUC→LHR 18:30 + BA73 LHR→LOS", description: "Rebook via evening LHR flight to Lagos.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "7F" }, available: true, estimatedArrival: "2026-03-02T05:30:00Z" },
    { id: "opt-206b", type: "alt_airport", summary: "Via FRA: LH110 + LH562 FRA→LOS", description: "Route via Frankfurt to Lagos.", details: { viaAirport: "FRA", connectingFlight: "LH562", transferMode: "train" as const, totalArrival: "2026-03-02T06:00:00Z" }, available: true, estimatedArrival: "2026-03-02T06:00:00Z" },
  ],
  "pax-207": [
    { id: "opt-207a", type: "rebook", summary: "LH2032 MUC→LHR 18:30, seat 10C", description: "Next direct flight to London this evening.", details: { flightNumber: "LH2032", origin: "MUC", destination: "LHR", departure: "2026-03-01T18:30:00Z", seatAvailable: "10C" }, available: true, estimatedArrival: "2026-03-01T20:00:00Z" },
  ],
};

const OPTIONS_DIS003: Record<string, Option[]> = {
  "pax-106": [
    { id: "opt-106a", type: "rebook", summary: "LH1832 MUC→FRA 18:00 + LH340 FRA→CAI", description: "Next FRA flight, connecting to Cairo.", details: { flightNumber: "LH1832", origin: "MUC", destination: "FRA", departure: "2026-03-01T18:00:00Z", seatAvailable: "14A" }, available: true, estimatedArrival: "2026-03-01T23:45:00Z" },
  ],
  "pax-110": [
    { id: "opt-110a", type: "rebook", summary: "LH1832 MUC→FRA 18:00 + LH902 FRA→IAD", description: "Next FRA flight, connecting to Washington.", details: { flightNumber: "LH1832", origin: "MUC", destination: "FRA", departure: "2026-03-01T18:00:00Z", seatAvailable: "6B" }, available: true, estimatedArrival: "2026-03-01T22:00:00Z" },
  ],
  "pax-114": [
    { id: "opt-114a", type: "rebook", summary: "LH1832 MUC→FRA 18:00 + LH710 FRA→NRT", description: "Next FRA flight, connecting to Tokyo.", details: { flightNumber: "LH1832", origin: "MUC", destination: "FRA", departure: "2026-03-01T18:00:00Z", seatAvailable: "3C" }, available: true, estimatedArrival: "2026-03-02T15:30:00Z" },
  ],
  "pax-120": [
    { id: "opt-120a", type: "rebook", summary: "LH1832 MUC→FRA 18:00 + LH450 FRA→ORD", description: "Next FRA flight, connecting to Chicago.", details: { flightNumber: "LH1832", origin: "MUC", destination: "FRA", departure: "2026-03-01T18:00:00Z", seatAvailable: "11D" }, available: true, estimatedArrival: "2026-03-01T22:15:00Z" },
  ],
  "pax-126": [
    { id: "opt-126a", type: "rebook", summary: "LH1832 MUC→FRA 18:00 + LH760 FRA→DEL", description: "Next FRA flight, connecting to Delhi.", details: { flightNumber: "LH1832", origin: "MUC", destination: "FRA", departure: "2026-03-01T18:00:00Z", seatAvailable: "8F" }, available: true, estimatedArrival: "2026-03-02T08:30:00Z" },
  ],
};

export const OPTIONS_MAP: Record<string, Record<string, Option[]>> = {
  "dis-001": OPTIONS_DIS001,
  "dis-002": OPTIONS_DIS002,
  "dis-003": OPTIONS_DIS003,
};

// ---- Wishes per disruption ----

export const WISHES_MAP: Record<string, Wish[]> = {
  "dis-001": [
    { id: "wish-001", passengerId: "pax-001", disruptionId: "dis-001", selectedOptionId: "opt-001a", rankedOptionIds: ["opt-001a", "opt-001b"], submittedAt: "2026-03-01T14:42:00Z", status: "pending" },
    { id: "wish-002", passengerId: "pax-002", disruptionId: "dis-001", selectedOptionId: "opt-002a", rankedOptionIds: ["opt-002a", "opt-002b"], submittedAt: "2026-03-01T14:45:00Z", status: "pending" },
    { id: "wish-003", passengerId: "pax-003", disruptionId: "dis-001", selectedOptionId: "opt-003a", rankedOptionIds: ["opt-003a", "opt-003b"], submittedAt: "2026-03-01T14:48:00Z", status: "pending" },
    { id: "wish-004", passengerId: "pax-004", disruptionId: "dis-001", selectedOptionId: "opt-002b", rankedOptionIds: ["opt-002b"], submittedAt: "2026-03-01T14:50:00Z", status: "pending" },
    { id: "wish-005", passengerId: "pax-005", disruptionId: "dis-001", selectedOptionId: "opt-002a", rankedOptionIds: ["opt-002a", "opt-002c"], submittedAt: "2026-03-01T14:53:00Z", status: "pending" },
    { id: "wish-006", passengerId: "pax-010", disruptionId: "dis-001", selectedOptionId: "opt-002b", rankedOptionIds: ["opt-002b", "opt-002a"], submittedAt: "2026-03-01T14:55:00Z", status: "pending" },
    { id: "wish-007", passengerId: "pax-008", disruptionId: "dis-001", selectedOptionId: "opt-002a", rankedOptionIds: ["opt-002a"], submittedAt: "2026-03-01T14:38:00Z", status: "approved", confirmationDetails: "Rebooked on LH1238, seat 12A. Boarding pass updated." },
    { id: "wish-008", passengerId: "pax-012", disruptionId: "dis-001", selectedOptionId: "opt-002b", rankedOptionIds: ["opt-002b", "opt-002a"], submittedAt: "2026-03-01T14:36:00Z", status: "approved", confirmationDetails: "Train ticket issued. MUC Hbf → Paris, departure 17:30." },
  ],
  "dis-002": [
    { id: "wish-201", passengerId: "pax-201", disruptionId: "dis-002", selectedOptionId: "opt-201a", rankedOptionIds: ["opt-201a", "opt-201b"], submittedAt: "2026-03-01T14:00:00Z", status: "pending" },
    { id: "wish-203", passengerId: "pax-203", disruptionId: "dis-002", selectedOptionId: "opt-203a", rankedOptionIds: ["opt-203a"], submittedAt: "2026-03-01T13:55:00Z", status: "pending" },
    { id: "wish-204", passengerId: "pax-204", disruptionId: "dis-002", selectedOptionId: "opt-204a", rankedOptionIds: ["opt-204a"], submittedAt: "2026-03-01T13:50:00Z", status: "approved", confirmationDetails: "Rebooked on LH2032, seat 22B. Boarding pass updated." },
    { id: "wish-207", passengerId: "pax-207", disruptionId: "dis-002", selectedOptionId: "opt-207a", rankedOptionIds: ["opt-207a"], submittedAt: "2026-03-01T14:05:00Z", status: "pending" },
  ],
  "dis-003": [
    { id: "wish-110", passengerId: "pax-110", disruptionId: "dis-003", selectedOptionId: "opt-110a", rankedOptionIds: ["opt-110a"], submittedAt: "2026-03-01T15:10:00Z", status: "pending" },
  ],
};

// Helper to build a full passenger profile
export function buildPassengerProfile(passengerId: string): PassengerProfile {
  const allPassengers = Object.values(PASSENGERS_MAP).flat();
  const passenger = allPassengers.find((p) => p.id === passengerId)!;
  const allOptions = Object.values(OPTIONS_MAP).reduce((acc, opts) => ({ ...acc, ...opts }), {} as Record<string, Option[]>);
  const options = allOptions[passengerId] ?? [];
  const allWishes = Object.values(WISHES_MAP).flat();
  const wishes = allWishes.filter((w) => w.passengerId === passengerId);
  return { ...passenger, options, wishes };
}
