package com.jvcodingsolutions.safelanding.core.data

import com.jvcodingsolutions.safelanding.core.domain.util.DataError
import com.jvcodingsolutions.safelanding.core.domain.util.Result
import com.jvcodingsolutions.safelanding.core.domain.util.SafeLandingRepository
import com.jvcodingsolutions.safelanding.core.domain.util.map
import com.jvcodingsolutions.safelanding.core.domain.util.model.Disruption
import com.jvcodingsolutions.safelanding.core.networking.dto.DisruptionDto
import com.jvcodingsolutions.safelanding.core.networking.get
import com.jvcodingsolutions.safelanding.core.networking.mapper.toDisruption
import io.ktor.client.HttpClient

class KtorRemoteSafeLandingDataSource(
    private val httpClient: HttpClient
): SafeLandingRepository {
    override suspend fun getDisruptions(): Result<List<Disruption>, DataError.Network> {
        return httpClient.get<List<DisruptionDto>>(
            route = "/disruptions",
        ).map { entries ->
            entries.map { it.toDisruption() }
        }
    }

    /*override suspend fun getDisruptionById(disruptionId: String): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/disruptions/$disruptionId",
        )
    }

    override suspend fun getPassengersByDisruptionId(disruptionId: String): Result<List<String>, DataError.Network> {
        return httpClient.get<List<String>>(
            route = "/disruptions/$disruptionId/passengers",
        )

    }

    override suspend fun getOptionsByDisruptionId(disruptionId: String): Result<List<String>, DataError.Network> {
        return httpClient.get<List<String>>(
            route = "/disruptions/$disruptionId/options",
        )
    }

    override suspend fun getDisruptionsByPassengerId(passengerId: String): Result<List<String>, DataError.Network> {
        return httpClient.get<List<String>>(
            route = "/passengers/$passengerId/disruptions",
        )
    }

    override suspend fun getOptionsByPassengerId(passengerId: String): Result<List<String>, DataError.Network> {
        return  httpClient.get<List<String>>(
            route = "/passengers/$passengerId/options",
        )
    }

    override suspend fun getStatusByPassengerId(passengerId: String): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/passengers/$passengerId/status",
        )
    }

    override suspend fun getProfileByPassengerId(passengerId: String): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/passengers/$passengerId/profile",
        )
    }

    override suspend fun getServiceLevelByPassengerId(passengerId: String): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/passengers/$passengerId/service-level",
        )
    }

    override suspend fun getWishes(): Result<List<String>, DataError.Network> {
        return httpClient.get<List<String>>(
            route = "/wishes",
        )
    }

    override suspend fun getLoungesByAirportCode(airportCode: String): Result<List<String>, DataError.Network> {
        return httpClient.get<List<String>>(
            route = "/api/lounges/$airportCode",
        )
    }

    override suspend fun getFlightStatusByFlightNumber(flightNumber: String): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/api/flights/$flightNumber/status",
        )
    }

    override suspend fun getSchedulesByOriginAndDestination(
        origin: String,
        destination: String
    ): Result<List<String>, DataError.Network> {
        return httpClient.get<List<String>>(
            route = "/api/schedules/$origin/$destination",
        )
    }

    override suspend fun getContextByFlightNumber(flightNumber: String): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/flights/$flightNumber/context",
        )
    }

    override suspend fun postWishByPassengerId(
        passengerId: String,
        wish: String
    ): Result<String, DataError.Network> {
        return httpClient.get<String>(
            route = "/passengers/$passengerId/wish",
        )
    }*/

}