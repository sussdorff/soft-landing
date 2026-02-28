package com.jvcodingsolutions.safelanding.navigation

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.ui.NavDisplay
import com.jvcodingsolutions.safelanding.features.options.OptionsScreen
import com.jvcodingsolutions.safelanding.features.status.StatusScreen
import com.jvcodingsolutions.safelanding.features.status.StatusScreenRoot

@Composable
fun SafeLandingNavigation(
    modifier: Modifier = Modifier
) {
    val navigationState = rememberNavigationState(
        startRoute = Route.StatusRoute,
        topLevelRoutes = TOP_LEVEL_DESTINATIONS.keys
    )
    val navigator = remember { Navigator(navigationState) }

    Scaffold(
        modifier = modifier,
        bottomBar = {
            NavigationBar {
                TOP_LEVEL_DESTINATIONS.forEach { (route, item) ->
                    NavigationBarItem(
                        selected = navigationState.topLevelRoute == route,
                        onClick = { navigator.navigate(route) },
                        icon = {
                            Icon(
                                imageVector = item.icon,
                                contentDescription = item.title
                            )
                        },
                        label = { Text(text = item.title) }
                    )
                }
            }
        }
    ) { innerPadding ->
        NavDisplay(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            onBack = navigator::goBack,
            entries = navigationState.toEntries(
                entryProvider {
                    entry<Route.StatusRoute> {
                        StatusScreenRoot()
                    }
                    entry<Route.OptionsRoute> {
                        OptionsScreen()
                    }
                }
            )
        )
    }
}
