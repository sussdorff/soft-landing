package com.jvcodingsolutions.safelanding.features.status

import com.jvcodingsolutions.safelanding.core.domain.util.model.Disruption

data class StatusState(
    val status: String = "Passenger Status",
    val disruptions: List<Disruption> = emptyList()
)
