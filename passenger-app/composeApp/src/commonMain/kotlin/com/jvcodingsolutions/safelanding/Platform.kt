package com.jvcodingsolutions.safelanding

interface Platform {
    val name: String
}

expect fun getPlatform(): Platform
