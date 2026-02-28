package com.jvcodingsolutions.safelanding.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation3.runtime.NavKey

data class NavigationItem(
    val title: String,
    val icon: ImageVector
)

val TOP_LEVEL_DESTINATIONS: Map<NavKey, NavigationItem> = mapOf(
    Route.StatusRoute to NavigationItem(
        title = "Status",
        icon = Icons.AutoMirrored.Filled.List
    ),
    Route.OptionsRoute to NavigationItem(
        title = "Options",
        icon = Icons.Filled.Settings
    )
)
