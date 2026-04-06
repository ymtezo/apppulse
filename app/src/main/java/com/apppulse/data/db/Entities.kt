package com.apppulse.data.db

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "usage_stats",
    indices = [Index("packageName", unique = true)]
)
data class UsageStatsEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val packageName: String,
    val appName: String,
    val totalForegroundSeconds: Long = 0,
    val totalLaunches: Int = 0,
    val lastUsed: Long = 0,     // epoch millis
    val firstSeen: Long = 0,
    val deviceId: String,
)

@Entity(
    tableName = "installed_apps",
    indices = [Index("packageName", unique = true)]
)
data class InstalledAppEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val packageName: String,
    val appName: String,
    val versionName: String? = null,
    val installedAt: Long = 0,
    val lastSeen: Long = System.currentTimeMillis(),
    val deviceId: String,
    val isSystemApp: Boolean = false,
)

@Entity(tableName = "deletion_log")
data class DeletionLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long = System.currentTimeMillis(),
    val packageName: String,
    val appName: String,
    val deviceId: String,
    val reason: String,            // "least_used", "manual"
    val usageRank: Int? = null,
    val totalForegroundSeconds: Long? = null,
    val success: Boolean = true,
)

@Entity(
    tableName = "uninstall_rejections",
    indices = [Index("packageName")]
)
data class UninstallRejectionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long = System.currentTimeMillis(),
    val packageName: String,
    val appName: String,
    val deviceId: String,
    val stage: String,  // "first", "final"
)
