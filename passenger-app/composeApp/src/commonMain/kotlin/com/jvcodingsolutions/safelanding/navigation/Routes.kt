package com.jvcodingsolutions.safelanding.navigation

import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

@Serializable
sealed interface Route : NavKey {

    @Serializable
    data object StatusRoute : Route, NavKey

    @Serializable
    data object OptionsRoute : Route, NavKey
}
