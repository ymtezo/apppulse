package com.apppulse

import android.app.Application
import android.util.Log
import com.apppulse.worker.WeeklyReportWorker

class AppPulseApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        try {
            WeeklyReportWorker.schedule(this)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to schedule weekly report worker", e)
        }
    }

    companion object {
        private const val TAG = "AppPulseApplication"
    }
}
