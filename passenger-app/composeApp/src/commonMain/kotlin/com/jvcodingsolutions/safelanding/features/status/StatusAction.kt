package com.jvcodingsolutions.safelanding.features.status

sealed interface StatusAction {
    data object OnShowOptions: StatusAction
}