package com.jvcodingsolutions.safelanding.navigation

import androidx.navigation3.runtime.NavKey

class Navigator(val state: NavigationState) {

    fun navigate(route: NavKey) {
        // Check if the target route is a Top Level Destination (Tab)
        if (route in state.backStacks.keys) {
            // Switch to this tab
            state.topLevelRoute = route

            // Reset the stack for this tab so we always land on the root of that tab
            state.backStacks[route]?.apply {
                clear()
                add(route)
            }
        } else {
            // Standard behavior: Push new screen onto the active stack
            state.backStacks[state.topLevelRoute]?.add(route)
        }
    }

    fun goBack() {
        val currentStack = state.backStacks[state.topLevelRoute]
            ?: error("Back stack for ${state.topLevelRoute} does not exist")

        val currentRoute = currentStack.lastOrNull()

        if (currentRoute == state.topLevelRoute) {
            // If at the root of the tab, go back to the start route
            if (state.topLevelRoute != state.startRoute) {
                state.topLevelRoute = state.startRoute
            }
        } else {
            // Pop the top screen
            currentStack.removeLastOrNull()
        }
    }
}
