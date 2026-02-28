package com.jvcodingsolutions.safelanding.features.status

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.runtime.getValue
import androidx.compose.ui.unit.dp
import org.koin.compose.viewmodel.koinViewModel


@Composable
fun StatusScreenRoot(
    modifier: Modifier = Modifier,
    viewModel: StatusViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    StatusScreen(
        modifier = modifier,
        onAction = viewModel::onAction,
        state = state
    )

}

@Composable
fun StatusScreen(
    modifier: Modifier = Modifier,
    onAction: (StatusAction) -> Unit,
    state: StatusState = StatusState()
) {
    Column(
        modifier = modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Status",
            style = MaterialTheme.typography.titleLarge
        )

        Text(
            text = state.status,
            style = MaterialTheme.typography.headlineMedium
        )

        state.disruptions.forEach { it ->
            Text(
                text = it.toString(),
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(8.dp))
        }
        Text(
            text = state.disruptions.toString()
        )
    }
}
