package com.jvcodingsolutions.safelanding.di

import com.jvcodingsolutions.safelanding.core.data.KtorRemoteSafeLandingDataSource
import com.jvcodingsolutions.safelanding.core.domain.util.SafeLandingRepository
import com.jvcodingsolutions.safelanding.core.networking.HttpClientFactory
import com.jvcodingsolutions.safelanding.features.status.StatusViewModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import org.koin.core.module.dsl.singleOf
import org.koin.core.module.dsl.viewModelOf
import org.koin.core.qualifier.named
import org.koin.dsl.bind
import org.koin.dsl.module

val appModule = module {
    single(named("AppScope")) {
        CoroutineScope(SupervisorJob() + Dispatchers.Default)
    }
    single {
        HttpClientFactory().build()
    }

    singleOf(::KtorRemoteSafeLandingDataSource). bind<SafeLandingRepository>()

    viewModelOf(::StatusViewModel)
}
