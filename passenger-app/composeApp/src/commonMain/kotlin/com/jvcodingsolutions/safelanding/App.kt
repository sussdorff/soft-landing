package com.jvcodingsolutions.safelanding

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import com.jvcodingsolutions.safelanding.navigation.SafeLandingNavigation

@Composable
fun App() {
    MaterialTheme {
        SafeLandingNavigation()
    }
}
