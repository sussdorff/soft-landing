package com.jvcodingsolutions.safelanding.features.status

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jvcodingsolutions.safelanding.core.domain.util.Result
import com.jvcodingsolutions.safelanding.core.domain.util.SafeLandingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class StatusViewModel(
    private val repository: SafeLandingRepository
): ViewModel() {
    private val _state = MutableStateFlow(StatusState())
    private var hasLoadedInitialData = false

    val state = _state
        .onStart {

            if (!hasLoadedInitialData) {
                getDisruptions()
                hasLoadedInitialData = true
            }
        }
        .stateIn(
            viewModelScope,
            SharingStarted.WhileSubscribed(5_000L),
            _state.value
        )

    fun onAction(action: StatusAction) {
        when(action) {
            StatusAction.OnShowOptions -> {}
        }
    }

    private fun getDisruptions() {
        viewModelScope.launch {
            when (val result = repository.getDisruptions()) {
                is Result.Success ->
                    _state.update { it.copy(
                        disruptions = result.data
                    )}

                is Result.Error -> {}
            }
        }

    }
}

// LH2072