package com.jvcodingsolutions.safelanding.core.domain.util.model

data class PassengerStatus(
    val passengerId: String,
    val name: String,
    val status: String,
    val denialCount: Int,
    val priority: Int
)

/*
{
    "passengerId": "pax-023",
    "name": "Amelie Laurent",
    "status": "notified",
    "denialCount": 0,
    "priority": 60
}*/
