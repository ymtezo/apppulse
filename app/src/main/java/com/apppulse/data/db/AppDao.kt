package com.apppulse.data.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface AppDao {

    // --- usage_stats ---

    @Upsert
    suspend fun upsertUsageStats(stats: UsageStatsEntity)

    @Query("""
        SELECT * FROM usage_stats
        WHERE deviceId = :deviceId
        ORDER BY totalForegroundSeconds DESC
    """)
    fun getUsageStatsByDevice(deviceId: String): Flow<List<UsageStatsEntity>>

    @Query("""
        SELECT * FROM usage_stats
        WHERE deviceId = :deviceId
        ORDER BY totalForegroundSeconds DESC
        LIMIT :limit
    """)
    suspend fun getTopApps(deviceId: String, limit: Int): List<UsageStatsEntity>

    @Query("""
        SELECT * FROM usage_stats
        WHERE deviceId = :deviceId AND totalForegroundSeconds > 0
        ORDER BY totalForegroundSeconds ASC
        LIMIT :limit
    """)
    suspend fun getBottomApps(deviceId: String, limit: Int): List<UsageStatsEntity>

    // --- installed_apps ---

    @Upsert
    suspend fun upsertInstalledApp(app: InstalledAppEntity)

    @Query("SELECT * FROM installed_apps WHERE deviceId = :deviceId ORDER BY appName")
    fun getInstalledApps(deviceId: String): Flow<List<InstalledAppEntity>>

    @Query("SELECT COUNT(*) FROM installed_apps WHERE deviceId = :deviceId")
    suspend fun getInstalledAppCount(deviceId: String): Int

    @Delete
    suspend fun deleteInstalledApp(app: InstalledAppEntity)

    @Query("DELETE FROM installed_apps WHERE packageName = :packageName AND deviceId = :deviceId")
    suspend fun removeInstalledApp(packageName: String, deviceId: String)

    // --- deletion_log ---

    @Insert
    suspend fun insertDeletionLog(log: DeletionLogEntity)

    @Query("SELECT * FROM deletion_log WHERE deviceId = :deviceId ORDER BY timestamp DESC")
    fun getDeletionLog(deviceId: String): Flow<List<DeletionLogEntity>>

    // --- uninstall_rejections ---

    @Insert
    suspend fun insertRejection(rejection: UninstallRejectionEntity)

    @Query("""
        SELECT COUNT(*) FROM uninstall_rejections
        WHERE packageName = :packageName AND deviceId = :deviceId
    """)
    suspend fun getRejectionCount(packageName: String, deviceId: String): Int

    @Query("""
        SELECT packageName, COUNT(*) as cnt
        FROM uninstall_rejections
        WHERE deviceId = :deviceId
        GROUP BY packageName
        ORDER BY cnt DESC
    """)
    suspend fun getRejectionSummary(deviceId: String): List<RejectionSummary>
}

data class RejectionSummary(
    val packageName: String,
    val cnt: Int,
)
