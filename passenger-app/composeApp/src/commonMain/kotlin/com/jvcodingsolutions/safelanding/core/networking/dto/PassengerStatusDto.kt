package com.jvcodingsolutions.safelanding.core.networking.dto

data class PassengerStatusDto(
    val passengerId: String,
    val name: String,
    val status: String,
    val denialCount: Int,
)
