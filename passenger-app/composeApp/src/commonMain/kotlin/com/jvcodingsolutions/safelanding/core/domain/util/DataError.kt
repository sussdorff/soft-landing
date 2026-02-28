package com.jvcodingsolutions.safelanding.core.domain.util

import com.jvcodingsolutions.safelanding.core.domain.util.Error

sealed interface DataError: Error {

    enum class Network: DataError {
        REQUEST_TIMEOUT,
        UNAUTHORIZED,
        CONFLICT,
        TOO_MANY_REQUESTS,
        NO_INTERNET,
        PAYLOAD_TOO_LARGE,
        SERVER_ERROR,
        SERIALIZATION,
        BAD_REQUEST,
        NOT_FOUND,
        UNKNOWN
    }

    enum class Local: DataError {
        DISK_FULL
    }
}