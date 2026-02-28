package com.jvcodingsolutions.safelanding.core.domain.util

import com.jvcodingsolutions.safelanding.core.domain.util.model.Disruption


interface SafeLandingRepository {

    // GET /disruptions
    suspend fun getDisruptions(): Result<List<Disruption>, DataError.Network>

    /*// GET /disruptions/{disruption_id}
    suspend fun getDisruptionById(disruptionId: String): Result<String, DataError.Network>

    // GET /disruptions/{disruption_id}/passengers
    suspend fun getPassengersByDisruptionId(disruptionId: String): Result<List<String>, DataError.Network>

    // GET /disruptions/{disruption_id}/options
    suspend fun getOptionsByDisruptionId(disruptionId: String): Result<List<String>, DataError.Network>

    // GET /passengers/{passenger_id}/disruptions
    suspend fun getDisruptionsByPassengerId(passengerId: String): Result<List<String>, DataError.Network>

    // GET /passengers/{passenger_id}/options
    suspend fun getOptionsByPassengerId(passengerId: String): Result<List<String>, DataError.Network>

    // GET /passengers/{passenger_id}/status
    suspend fun getStatusByPassengerId(passengerId: String): Result<String, DataError.Network>

   // GET /passengers/{passenger_id}/profile
    suspend fun getProfileByPassengerId(passengerId: String): Result<String, DataError.Network>

    // GET /passengers/{passenger_id}/service-level
    suspend fun getServiceLevelByPassengerId(passengerId: String): Result<String, DataError.Network>

    // GET /wishes
    suspend fun getWishes(): Result<List<String>, DataError.Network>

    // GET /api/lounges/{airport_code}
    suspend fun getLoungesByAirportCode(airportCode: String): Result<List<String>, DataError.Network>

    // GET /api/flights/{flight_number}/status
    suspend fun getFlightStatusByFlightNumber(flightNumber: String): Result<String, DataError.Network>

    // GET /api/schedules/{origin}/{destination}
    suspend fun getSchedulesByOriginAndDestination(origin: String, destination: String): Result<List<String>, DataError.Network>

    // GET /flights/{flight_number}/context
    suspend fun getContextByFlightNumber(flightNumber: String): Result<String, DataError.Network>

    //POST /passengers/{passenger_id}/wish
    suspend fun postWishByPassengerId(passengerId: String, wish: String): Result<String, DataError.Network>*/

}







