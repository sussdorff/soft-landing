package com.jvcodingsolutions.safelanding.core.networking.dto

import kotlinx.serialization.Serializable

@Serializable
data class DisruptionDto(
    val id: String,
    val type: String,
    val flightNumber: String,
    val origin: String,
    val destination: String,
    val reason: String,
    val explanation: String,
    val detectedAt: String,
    val affectedPassengerIds: List<String>
)
