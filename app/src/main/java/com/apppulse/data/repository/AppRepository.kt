package com.apppulse.data.repository

import com.apppulse.data.db.*
import kotlinx.coroutines.flow.Flow

class AppRepository(private val dao: AppDao) {

    fun getUsageStats(deviceId: String): Flow<List<UsageStatsEntity>> =
        dao.getUsageStatsByDevice(deviceId)

    suspend fun getTopApps(deviceId: String, limit: Int = 10) =
        dao.getTopApps(deviceId, limit)

    suspend fun getBottomApps(deviceId: String, limit: Int = 10) =
        dao.getBottomApps(deviceId, limit)

    suspend fun upsertUsageStats(stats: UsageStatsEntity) =
        dao.upsertUsageStats(stats)

    // Installed apps
    fun getInstalledApps(deviceId: String): Flow<List<InstalledAppEntity>> =
        dao.getInstalledApps(deviceId)

    suspend fun getInstalledAppCount(deviceId: String) =
        dao.getInstalledAppCount(deviceId)

    suspend fun upsertInstalledApp(app: InstalledAppEntity) =
        dao.upsertInstalledApp(app)

    suspend fun removeInstalledApp(packageName: String, deviceId: String) =
        dao.removeInstalledApp(packageName, deviceId)

    // Deletion log
    fun getDeletionLog(deviceId: String): Flow<List<DeletionLogEntity>> =
        dao.getDeletionLog(deviceId)

    suspend fun logDeletion(log: DeletionLogEntity) =
        dao.insertDeletionLog(log)

    // Rejections
    suspend fun logRejection(rejection: UninstallRejectionEntity) =
        dao.insertRejection(rejection)

    suspend fun getRejectionCount(packageName: String, deviceId: String) =
        dao.getRejectionCount(packageName, deviceId)

    suspend fun getRejectionSummary(deviceId: String) =
        dao.getRejectionSummary(deviceId)
}
