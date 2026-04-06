package com.apppulse.ui.screens

import android.app.Application
import android.os.Build
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.apppulse.data.db.AppDatabase
import com.apppulse.data.db.DeletionLogEntity
import com.apppulse.data.db.UninstallRejectionEntity
import com.apppulse.data.db.UsageStatsEntity
import com.apppulse.data.repository.AppRepository
import com.apppulse.recommender.Alternative
import com.apppulse.recommender.AlternativesDb
import com.apppulse.tracker.UsageTracker
import com.apppulse.worker.WeeklyReportWorker
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class AppItem(
    val packageName: String,
    val appName: String,
    val foregroundTime: String,
    val foregroundSeconds: Long,
    val rejectionCount: Int = 0,
    val alternatives: List<Alternative> = emptyList(),
)

data class DashboardUiState(
    val topApps: List<AppItem> = emptyList(),
    val bottomApps: List<AppItem> = emptyList(),
    val installedCount: Int = 0,
    val isLoading: Boolean = true,
    val hasPermission: Boolean = false,
    val deviceId: String = "",
    val error: String? = null,
)

class DashboardViewModel(application: Application) : AndroidViewModel(application) {

    private val db = AppDatabase.getInstance(application)
    private val repo = AppRepository(db.appDao())
    val deviceId: String = Build.MODEL
    private val tracker = UsageTracker(application, repo, deviceId)

    private val _uiState = MutableStateFlow(DashboardUiState(deviceId = deviceId))
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    val deletionLog = repo.getDeletionLog(deviceId)
        .stateIn(viewModelScope, SharingStarted.Lazily, emptyList())

    init {
        checkPermissionAndLoad()
    }

    fun checkPermissionAndLoad() {
        viewModelScope.launch {
            val hasPerm = tracker.hasPermission()
            _uiState.update { it.copy(hasPermission = hasPerm) }
            if (hasPerm) refresh()
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            try {
                tracker.collectUsageStats(days = 7)
                tracker.scanInstalledApps()

                val top = repo.getTopApps(deviceId, 15)
                val bottom = repo.getBottomApps(deviceId, 15)
                val count = repo.getInstalledAppCount(deviceId)

                _uiState.update {
                    it.copy(
                        topApps = top.map { s -> s.toAppItem() },
                        bottomApps = bottom.map { s -> s.toAppItem() },
                        installedCount = count,
                        isLoading = false,
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to refresh dashboard", e)
                _uiState.update {
                    it.copy(isLoading = false, error = "データの取得に失敗しました: ${e.localizedMessage}")
                }
            }
        }
    }

    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    fun requestUninstall(
        packageName: String,
        appName: String,
        onConfirm: (confirmed: Boolean, rejections: Int, warningLevel: String) -> Unit,
    ) {
        viewModelScope.launch {
            val rejections = repo.getRejectionCount(packageName, deviceId)
            val level = when {
                rejections > 5 -> "重要警告"
                rejections > 2 -> "警告"
                rejections > 0 -> "注意"
                else -> "通常"
            }
            onConfirm(true, rejections, level)
        }
    }

    fun logRejection(packageName: String, appName: String, stage: String) {
        viewModelScope.launch {
            repo.logRejection(
                UninstallRejectionEntity(
                    packageName = packageName,
                    appName = appName,
                    deviceId = deviceId,
                    stage = stage,
                )
            )
        }
    }

    fun logDeletion(packageName: String, appName: String, reason: String, success: Boolean) {
        viewModelScope.launch {
            try {
                repo.logDeletion(
                    DeletionLogEntity(
                        packageName = packageName,
                        appName = appName,
                        deviceId = deviceId,
                        reason = reason,
                        success = success,
                    )
                )
                if (success) {
                    repo.removeInstalledApp(packageName, deviceId)
                }
                refresh()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to log deletion for $packageName", e)
            }
        }
    }

    private suspend fun UsageStatsEntity.toAppItem(): AppItem {
        val rejections = try {
            repo.getRejectionCount(packageName, deviceId)
        } catch (e: Exception) {
            0
        }
        return AppItem(
            packageName = packageName,
            appName = appName,
            foregroundTime = WeeklyReportWorker.formatDuration(totalForegroundSeconds),
            foregroundSeconds = totalForegroundSeconds,
            rejectionCount = rejections,
            alternatives = AlternativesDb.getAlternatives(packageName),
        )
    }

    companion object {
        private const val TAG = "DashboardViewModel"
    }
}
