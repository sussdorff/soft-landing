package com.jvcodingsolutions.safelanding.core.networking.dto

import kotlinx.serialization.Serializable

@Serializable
data class PassengerDto(
    val id: String,
    val name: String,
    val bookingRef: String,
    val originalItinerary: List<ItineraryDto>,
    val status: String,
    val denialCount: Int,
    val priority: Int,
    val loyaltyTier: String,
    val bookingClass: String,
    val cabinClass: String

)

@Serializable
data class ItineraryDto(
    val flightNumber: String,
    val origin: String,
    val destination: String,
    val departure: String,
    val arrival: String
)

