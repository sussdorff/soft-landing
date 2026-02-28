package com.jvcodingsolutions.androidapp.app

import android.app.Application
import com.jvcodingsolutions.safelanding.di.initKoin
import org.koin.android.ext.koin.androidContext
import org.koin.android.ext.koin.androidLogger
import timber.log.Timber
import com.jvcodingsolutions.safelanding.androidapp.BuildConfig

class SafeLandingApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }

        initKoin {
            androidContext(this@SafeLandingApplication)
            androidLogger()
        }
    }
}
