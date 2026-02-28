// ============================================================
// Soft Landing — Shared Types (from docs/architecture.md)
// ============================================================

export interface Segment {
  flightNumber: string;
  origin: string;
  destination: string;
  departure: string; // ISO 8601
  arrival: string;
}

export interface Itinerary {
  segments: Segment[];
}

export type PassengerStatus =
  | "unaffected"
  | "notified"
  | "chose"
  | "approved"
  | "denied";

export interface Passenger {
  id: string;
  name: string;
  bookingRef: string;
  originalItinerary: Itinerary;
  status: PassengerStatus;
  denialCount: number;
  priority: number; // 0 = normal, 1 = elevated (1 denial), 2 = critical (2+ denials)
}

export type DisruptionType = "cancellation" | "diversion" | "delay";

export interface Disruption {
  id: string;
  type: DisruptionType;
  flightNumber: string;
  origin: string;
  destination: string;
  reason: string;
  explanation: string; // Gemini plain-language
  detectedAt: string;
  affectedPassengerIds: string[];
}

export type OptionType = "rebook" | "hotel" | "ground" | "alt_airport";

export interface RebookDetails {
  flightNumber: string;
  origin: string;
  destination: string;
  departure: string;
  seatAvailable: string;
}

export interface HotelDetails {
  hotelName: string;
  address: string;
  location: { lat: number; lng: number };
  nextFlightNumber: string;
  nextFlightDeparture: string;
}

export interface GroundTransportDetails {
  mode: "train" | "bus";
  route: string;
  departure: string;
  arrival: string;
  provider: string;
}

export interface AltAirportDetails {
  viaAirport: string;
  connectingFlight: string;
  transferMode: "train" | "bus" | "taxi";
  totalArrival: string;
}

export type OptionDetails =
  | RebookDetails
  | HotelDetails
  | GroundTransportDetails
  | AltAirportDetails;

export interface Option {
  id: string;
  type: OptionType;
  summary: string;
  description: string;
  details: OptionDetails;
  available: boolean;
  estimatedArrival: string;
}

export type WishStatus = "pending" | "approved" | "denied";

export interface Wish {
  id: string;
  passengerId: string;
  disruptionId: string;
  selectedOptionId: string;
  rankedOptionIds: string[];
  submittedAt: string;
  status: WishStatus;
  denialReason?: string;
  confirmationDetails?: string;
}

// Passenger profile for manual resolution view
export interface PassengerProfile extends Passenger {
  options: Option[];
  wishes: Wish[];
}

// WebSocket event types
export type WSEventType =
  | "new_wish"
  | "wish_approved"
  | "wish_denied"
  | "disruption_created"
  | "options_updated";

export interface WSEvent<T = unknown> {
  type: WSEventType;
  timestamp: string;
  data: T;
}

// Dashboard API interface — both mock and real adapters implement this
export interface DashboardAPI {
  getDisruption(id: string): Promise<Disruption>;
  getPassengers(disruptionId: string): Promise<Passenger[]>;
  getWishes(disruptionId: string): Promise<Wish[]>;
  getPassengerProfile(passengerId: string): Promise<PassengerProfile>;
  approveWish(wishId: string): Promise<void>;
  denyWish(wishId: string, reason: string): Promise<void>;
  resolveManually(passengerId: string, optionId: string, disruptionId: string): Promise<Wish>;
  onEvent(handler: (event: WSEvent) => void): () => void; // returns unsubscribe
}
