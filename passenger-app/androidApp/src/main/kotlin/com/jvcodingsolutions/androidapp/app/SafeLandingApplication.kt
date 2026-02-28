package com.jvcodingsolutions.androidapp.app

import android.app.Application
import com.jvcodingsolutions.safelanding.di.initKoin
import org.koin.android.ext.koin.androidContext
import org.koin.android.ext.koin.androidLogger

class SafeLandingApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        initKoin {
            androidContext(this@SafeLandingApplication)
            androidLogger()
        }
    }
}
