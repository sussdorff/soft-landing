package com.jvcodingsolutions.safelanding.core.domain.util.model

data class Passenger(
    val id: String,
    val name: String,
    val bookingRef: String,
    val originalItinerary: List<Itinerary>,
    val status: String,
    val denialCount: Int,
    val priority: Int,
    val loyaltyTier: String,
    val bookingClass: String,
    val cabinClass: String

)

data class Itinerary(
    val flightNumber: String,
    val origin: String,
    val destination: String,
    val departure: String,
    val arrival: String
)



/*
{
    "id": "pax-210",
    "name": "Tobias Wagner",
    "bookingRef": "1IOR56",
    "originalItinerary": [
    {
        "flightNumber": "LH2072",
        "origin": "MUC",
        "destination": "HAM",
        "departure": "2026-02-28T17:51:00.619888Z",
        "arrival": "2026-02-28T19:06:00.619888Z"
    }
    ],
    "status": "notified",
    "denialCount": 0,
    "priority": 60,
    "loyaltyTier": "hon",
    "bookingClass": "J",
    "cabinClass": "business"
},*/
