package com.jvcodingsolutions.safelanding.core.domain.util.model

import kotlinx.datetime.Instant
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Enums ─────────────────────────────────────────────────────────────────────

@Serializable
enum class TransferMode {
    @SerialName("train") TRAIN,
    @SerialName("bus")   BUS,
    @SerialName("taxi")  TAXI,
}

@Serializable
enum class GroundMode {
    @SerialName("train") TRAIN,
    @SerialName("bus")   BUS,
}

// ── Detail Data Classes ───────────────────────────────────────────────────────

@Serializable
data class RebookDetails(
    val flightNumber: String,
    val origin: String,
    val destination: String,
    val departure: Instant,
    val seatAvailable: Boolean = true,
)

@Serializable
data class Location(
    val lat: Double,
    val lng: Double,
)

@Serializable
data class HotelDetails(
    val hotelName: String,
    val address: String,
    val location: Location,
    val nextFlightNumber: String,
    val nextFlightDeparture: Instant,
)

@Serializable
data class GroundTransportDetails(
    val mode: GroundMode,
    val route: String,
    val departure: Instant,
    val arrival: Instant,
    val provider: String,
)

@Serializable
data class AltAirportDetails(
    val viaAirport: String,
    val connectingFlight: String,
    val transferMode: TransferMode,
    val totalArrival: Instant,
)

// ── Sealed Interface ──────────────────────────────────────────────────────────

@Serializable
sealed interface Option {
    val id: String
    val summary: String
    val description: String
    val available: Boolean
    val estimatedArrival: Instant

    @Serializable
    @SerialName("rebook")
    data class Rebook(
        override val id: String,
        override val summary: String,
        override val description: String,
        override val available: Boolean,
        override val estimatedArrival: Instant,
        val details: RebookDetails,
    ) : Option

    @Serializable
    @SerialName("hotel")
    data class Hotel(
        override val id: String,
        override val summary: String,
        override val description: String,
        override val available: Boolean,
        override val estimatedArrival: Instant,
        val details: HotelDetails,
    ) : Option

    @Serializable
    @SerialName("ground")
    data class Ground(
        override val id: String,
        override val summary: String,
        override val description: String,
        override val available: Boolean,
        override val estimatedArrival: Instant,
        val details: GroundTransportDetails,
    ) : Option

    @Serializable
    @SerialName("alt_airport")
    data class AltAirport(
        override val id: String,
        override val summary: String,
        override val description: String,
        override val available: Boolean,
        override val estimatedArrival: Instant,
        val details: AltAirportDetails,
    ) : Option
}


/*
[
    {
        "id": "4ac47f13",
        "type": "rebook",
        "summary": "Next available flight to ALL",
        "description": "Option: rebook. flight_number: LHXXXX, origin: MUC, destination: ALL, departure: 2026-03-01T08:00:00+00:00, seat_available: True",
        "details": {
        "flightNumber": "LHXXXX",
        "origin": "MUC",
        "destination": "ALL",
        "departure": "2026-03-01T08:00:00Z",
        "seatAvailable": true
    },
        "available": true,
        "estimatedArrival": "2026-03-01T10:00:00Z"
    },
    {
        "id": "e8ac4e47",
        "type": "hotel",
        "summary": "Overnight at Airport Hotel",
        "description": "Option: hotel. hotel_name: Airport Hotel, address: Airport Terminal Area, location: {'lat': 48.354, 'lng': 11.775}, next_flight_number: LHXXXX, next_flight_departure: 2026-03-01T07:00:00+00:00, stars: 3, price_per_night: 80, maps_uri: , rating: 3.5",
        "details": {
        "hotelName": "Airport Hotel",
        "address": "Airport Terminal Area",
        "location": {
        "lat": 48.354,
        "lng": 11.775
    },
        "nextFlightNumber": "LHXXXX",
        "nextFlightDeparture": "2026-03-01T07:00:00Z",
        "stars": 3,
        "pricePerNight": 80,
        "mapsUri": "",
        "rating": "3.5"
    },
        "available": true,
        "estimatedArrival": "2026-03-01T10:00:00Z"
    },
    {
        "id": "7a5a5973",
        "type": "ground",
        "summary": "Limousine to ALL",
        "description": "Option: ground. mode: taxi, route: Limousine to ALL, departure: 2026-02-28T17:03:51.219505+00:00, arrival: 2026-02-28T20:03:51.219505+00:00, provider: Limousine",
        "details": {
        "mode": "taxi",
        "route": "Limousine to ALL",
        "departure": "2026-02-28T17:03:51.219505Z",
        "arrival": "2026-02-28T20:03:51.219505Z",
        "provider": "Limousine"
    },
        "available": true,
        "estimatedArrival": "2026-02-28T20:03:51.219505Z"
    }
]*/
