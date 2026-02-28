package com.jvcodingsolutions.safelanding.di

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import org.koin.core.qualifier.named
import org.koin.dsl.module

val appModule = module {
    single(named("AppScope")) {
        CoroutineScope(SupervisorJob() + Dispatchers.Default)
    }
}
