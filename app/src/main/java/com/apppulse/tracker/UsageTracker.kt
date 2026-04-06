package com.apppulse.tracker

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import com.apppulse.data.db.InstalledAppEntity
import com.apppulse.data.db.UsageStatsEntity
import com.apppulse.data.repository.AppRepository

class UsageTracker(
    private val context: Context,
    private val repository: AppRepository,
    private val deviceId: String,
) {

    private val usageStatsManager =
        context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
    private val packageManager = context.packageManager

    fun hasPermission(): Boolean {
        val manager = usageStatsManager ?: return false
        return try {
            val now = System.currentTimeMillis()
            val stats = manager.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY,
                now - 60_000, now
            )
            stats != null && stats.isNotEmpty()
        } catch (e: SecurityException) {
            Log.w(TAG, "Usage stats permission denied", e)
            false
        }
    }

    suspend fun collectUsageStats(days: Int = 7) {
        val manager = usageStatsManager ?: run {
            Log.w(TAG, "UsageStatsManager unavailable")
            return
        }

        val now = System.currentTimeMillis()
        val start = now - days.toLong() * 24 * 60 * 60 * 1000

        val stats = try {
            manager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start, now)
        } catch (e: SecurityException) {
            Log.w(TAG, "Failed to query usage stats", e)
            return
        } ?: return

        val aggregated = mutableMapOf<String, AggregatedStats>()
        for (stat in stats) {
            val pkg = stat.packageName
            val existing = aggregated.getOrPut(pkg) {
                AggregatedStats(pkg, 0, 0, 0, Long.MAX_VALUE)
            }
            aggregated[pkg] = existing.copy(
                totalForegroundMs = existing.totalForegroundMs + stat.totalTimeInForeground,
                lastUsed = maxOf(existing.lastUsed, stat.lastTimeUsed),
                firstSeen = minOf(existing.firstSeen, stat.firstTimeStamp),
            )
        }

        for ((pkg, agg) in aggregated) {
            if (agg.totalForegroundMs <= 0) continue
            val appName = getAppName(pkg)
            try {
                repository.upsertUsageStats(
                    UsageStatsEntity(
                        packageName = pkg,
                        appName = appName,
                        totalForegroundSeconds = agg.totalForegroundMs / 1000,
                        totalLaunches = agg.launches,
                        lastUsed = agg.lastUsed,
                        firstSeen = if (agg.firstSeen == Long.MAX_VALUE) now else agg.firstSeen,
                        deviceId = deviceId,
                    )
                )
            } catch (e: Exception) {
                Log.e(TAG, "Failed to upsert usage stats for $pkg", e)
            }
        }
    }

    suspend fun scanInstalledApps() {
        val apps = try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getInstalledApplications(
                    PackageManager.ApplicationInfoFlags.of(0)
                )
            } else {
                @Suppress("DEPRECATION")
                packageManager.getInstalledApplications(0)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get installed applications", e)
            return
        }

        val now = System.currentTimeMillis()
        for (appInfo in apps) {
            try {
                val isSystem = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                val appName = packageManager.getApplicationLabel(appInfo).toString()

                repository.upsertInstalledApp(
                    InstalledAppEntity(
                        packageName = appInfo.packageName,
                        appName = appName,
                        installedAt = appInfo.firstInstallTime,
                        lastSeen = now,
                        deviceId = deviceId,
                        isSystemApp = isSystem,
                    )
                )
            } catch (e: Exception) {
                Log.e(TAG, "Failed to process app ${appInfo.packageName}", e)
            }
        }
    }

    private fun getAppName(packageName: String): String {
        return try {
            val appInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getApplicationInfo(
                    packageName, PackageManager.ApplicationInfoFlags.of(0)
                )
            } else {
                @Suppress("DEPRECATION")
                packageManager.getApplicationInfo(packageName, 0)
            }
            packageManager.getApplicationLabel(appInfo).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            packageName.substringAfterLast('.')
        }
    }

    private data class AggregatedStats(
        val packageName: String,
        val totalForegroundMs: Long,
        val launches: Int,
        val lastUsed: Long,
        val firstSeen: Long,
    )

    companion object {
        private const val TAG = "UsageTracker"
    }
}
