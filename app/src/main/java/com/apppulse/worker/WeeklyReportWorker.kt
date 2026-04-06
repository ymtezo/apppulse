package com.apppulse.worker

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.*
import com.apppulse.MainActivity
import com.apppulse.data.db.AppDatabase
import com.apppulse.data.repository.AppRepository
import com.apppulse.recommender.AlternativesDb
import com.apppulse.tracker.UsageTracker
import java.util.concurrent.TimeUnit

class WeeklyReportWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val db = AppDatabase.getInstance(applicationContext)
            val repo = AppRepository(db.appDao())
            val deviceId = Build.MODEL
            val tracker = UsageTracker(applicationContext, repo, deviceId)

            // 1. Collect usage stats
            tracker.collectUsageStats(days = 7)

            // 2. Scan installed apps
            tracker.scanInstalledApps()

            // 3. Get top/bottom apps
            val top = repo.getTopApps(deviceId, 5)
            val bottom = repo.getBottomApps(deviceId, 5)

            // 4. Show notification with summary
            if (top.isNotEmpty()) {
                showSummaryNotification(
                    topApp = top.first().appName,
                    topTime = formatDuration(top.first().totalForegroundSeconds),
                    bottomApp = bottom.firstOrNull()?.appName ?: "-",
                    bottomTime = formatDuration(bottom.firstOrNull()?.totalForegroundSeconds ?: 0),
                )
            }

            // 5. Show recommendation for top app
            if (top.isNotEmpty()) {
                val alts = AlternativesDb.getAlternatives(top.first().packageName)
                if (alts.isNotEmpty()) {
                    showRecommendationNotification(
                        appName = top.first().appName,
                        altName = alts.first().name,
                        altReason = alts.first().reason,
                        altPackageId = alts.first().packageId,
                    )
                }
            }

            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "Weekly report failed", e)
            if (runAttemptCount < MAX_RETRIES) Result.retry() else Result.failure()
        }
    }

    private fun showSummaryNotification(
        topApp: String, topTime: String,
        bottomApp: String, bottomTime: String,
    ) {
        ensureChannel()
        if (!hasNotificationPermission()) return

        val intent = Intent(applicationContext, MainActivity::class.java)
        val pending = PendingIntent.getActivity(
            applicationContext, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setContentTitle("AppPulse 週次サマリー")
            .setContentText("最も使用: $topApp ($topTime)")
            .setStyle(NotificationCompat.BigTextStyle().bigText(
                "最も使用: $topApp ($topTime)\n" +
                "最も未使用: $bottomApp ($bottomTime)\n\n" +
                "タップしてダッシュボードを確認"
            ))
            .setContentIntent(pending)
            .setAutoCancel(true)
            .build()

        try {
            NotificationManagerCompat.from(applicationContext)
                .notify(SUMMARY_NOTIFICATION_ID, notification)
        } catch (e: SecurityException) {
            Log.w(TAG, "Notification permission revoked", e)
        }
    }

    private fun showRecommendationNotification(
        appName: String, altName: String,
        altReason: String, altPackageId: String?,
    ) {
        ensureChannel()
        if (!hasNotificationPermission()) return

        val builder = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentTitle("$appName の代替アプリ")
            .setContentText("$altName: $altReason")
            .setAutoCancel(true)

        // Add "Open Play Store" action
        if (altPackageId != null) {
            val storeIntent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse("market://details?id=$altPackageId")
            )
            val storePending = PendingIntent.getActivity(
                applicationContext, 1, storeIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            builder.addAction(
                android.R.drawable.ic_menu_add,
                "Play Storeで見る",
                storePending,
            )
        }

        try {
            NotificationManagerCompat.from(applicationContext)
                .notify(RECOMMEND_NOTIFICATION_ID, builder.build())
        } catch (e: SecurityException) {
            Log.w(TAG, "Notification permission revoked", e)
        }
    }

    private fun ensureChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID, "AppPulse レポート",
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = "週次使用状況レポートとレコメンド通知"
        }
        val manager = applicationContext.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    private fun hasNotificationPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(
                applicationContext, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        } else true
    }

    companion object {
        private const val TAG = "WeeklyReportWorker"
        private const val MAX_RETRIES = 3
        const val CHANNEL_ID = "apppulse_reports"
        const val SUMMARY_NOTIFICATION_ID = 1001
        const val RECOMMEND_NOTIFICATION_ID = 1002
        const val WORK_NAME = "apppulse_weekly_report"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<WeeklyReportWorker>(
                7, TimeUnit.DAYS,
            ).setInitialDelay(
                calculateDelayToSaturday(), TimeUnit.MILLISECONDS,
            ).build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }

        private fun calculateDelayToSaturday(): Long {
            val now = java.util.Calendar.getInstance()
            val saturday = java.util.Calendar.getInstance().apply {
                set(java.util.Calendar.DAY_OF_WEEK, java.util.Calendar.SATURDAY)
                set(java.util.Calendar.HOUR_OF_DAY, 10)
                set(java.util.Calendar.MINUTE, 0)
                set(java.util.Calendar.SECOND, 0)
                if (before(now)) add(java.util.Calendar.WEEK_OF_YEAR, 1)
            }
            return saturday.timeInMillis - now.timeInMillis
        }

        fun formatDuration(seconds: Long): String = when {
            seconds < 60 -> "${seconds}秒"
            seconds < 3600 -> "${seconds / 60}分"
            else -> {
                val h = seconds / 3600
                val m = (seconds % 3600) / 60
                if (m > 0) "${h}時間${m}分" else "${h}時間"
            }
        }
    }
}
