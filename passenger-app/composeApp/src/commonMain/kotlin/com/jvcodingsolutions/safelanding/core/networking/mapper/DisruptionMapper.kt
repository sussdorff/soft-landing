package com.jvcodingsolutions.safelanding.core.networking.mapper

import com.jvcodingsolutions.safelanding.core.domain.util.model.Disruption
import com.jvcodingsolutions.safelanding.core.networking.dto.DisruptionDto

fun Disruption.toDisruptionDto(): DisruptionDto {
    return DisruptionDto(
        id = id,
        type = type,
        flightNumber = flightNumber,
        origin = origin,
        destination = destination,
        reason = reason,
        explanation = explanation,
        detectedAt = detectedAt,
        affectedPassengerIds = affectedPassengerIds
    )
}

fun DisruptionDto.toDisruption(): Disruption {
    return Disruption(
        id = id,
        type = type,
        flightNumber = flightNumber,
        origin = origin,
        destination = destination,
        reason = reason,
        explanation = explanation,
        detectedAt = detectedAt,
        affectedPassengerIds = affectedPassengerIds
    )
}