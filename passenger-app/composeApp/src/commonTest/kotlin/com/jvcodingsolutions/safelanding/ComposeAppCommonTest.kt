package com.jvcodingsolutions.safelanding

import kotlin.test.Test
import kotlin.test.assertTrue

class ComposeAppCommonTest {

    @Test
    fun platformNameIsNotEmpty() {
        assertTrue(getPlatform().name.isNotEmpty())
    }
}
