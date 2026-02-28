package com.jvcodingsolutions.safelanding.core.presentation.util

import com.jvcodingsolutions.safelanding.core.domain.util.DataError


fun DataError.asUiText(): UiText {
    return when(this) {
        DataError.Local.DISK_FULL -> UiText.DynamicString(
            "Error: Disk is full."
        )

        DataError.Network.REQUEST_TIMEOUT -> UiText.DynamicString(
            "Error Request Timeout"
        )

        DataError.Network.TOO_MANY_REQUESTS -> UiText.DynamicString(
            "Error To many requests"
        )
        DataError.Network.NO_INTERNET -> UiText.DynamicString(
            "Error No internet"
        )
        DataError.Network.PAYLOAD_TOO_LARGE -> UiText.DynamicString(
            "Error Payload too large"
        )
        DataError.Network.SERVER_ERROR -> UiText.DynamicString(
            "Error Server error"
        )
        DataError.Network.SERIALIZATION -> UiText.DynamicString(
            "Error Serialization"
        )
        DataError.Network.BAD_REQUEST -> UiText.DynamicString(
            "Error Bad request"
        )
        else -> UiText.DynamicString(
            "Unknown Error"
        )
    }

}