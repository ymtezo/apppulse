package com.apppulse.ota

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.apppulse.R
import java.util.concurrent.TimeUnit

class OtaUpdateWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val versionUrl = applicationContext.getString(R.string.ota_version_url)
        val result = OtaUpdateManager(applicationContext).checkAndUpdate(versionUrl)
        Log.i("OtaUpdateWorker", "OTA check result: ${result.message}")
        return Result.success()
    }

    companion object {
        private const val WORK_NAME = "apppulse_ota"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<OtaUpdateWorker>(1, TimeUnit.DAYS)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        }
    }
}
