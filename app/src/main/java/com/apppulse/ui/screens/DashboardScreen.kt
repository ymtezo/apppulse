package com.apppulse.ui.screens

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(viewModel: DashboardViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(0) }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.error) {
        uiState.error?.let { message ->
            snackbarHostState.showSnackbar(
                message = message,
                actionLabel = "再試行",
                duration = SnackbarDuration.Long,
            ).let { result ->
                if (result == SnackbarResult.ActionPerformed) {
                    viewModel.refresh()
                }
            }
            viewModel.clearError()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AppPulse [${uiState.deviceId}]") },
                actions = {
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(Icons.Default.Refresh, "更新")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            if (!uiState.hasPermission) {
                PermissionBanner {
                    context.startActivity(
                        Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                    )
                }
            }

            TabRow(selectedTabIndex = selectedTab) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 },
                    text = { Text("使用状況") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 },
                    text = { Text("未使用") })
                Tab(selected = selectedTab == 2, onClick = { selectedTab = 2 },
                    text = { Text("削除ログ") })
            }

            when (selectedTab) {
                0 -> TopAppsTab(uiState, viewModel)
                1 -> BottomAppsTab(uiState, viewModel)
                2 -> DeletionLogTab(viewModel)
            }
        }
    }
}

@Composable
private fun PermissionBanner(onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer,
        ),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Default.Warning, null,
                tint = MaterialTheme.colorScheme.error,
                modifier = Modifier.size(24.dp))
            Spacer(Modifier.width(12.dp))
            Column {
                Text("使用状況アクセスが必要です",
                    fontWeight = FontWeight.Bold)
                Text("タップして設定画面を開き、AppPulseを許可してください",
                    style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun TopAppsTab(uiState: DashboardUiState, viewModel: DashboardViewModel) {
    if (uiState.isLoading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Text("インストール済み: ${uiState.installedCount}件",
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.padding(bottom = 8.dp))
        }
        items(uiState.topApps) { app ->
            AppUsageCard(app, showBar = true, maxSeconds = uiState.topApps.firstOrNull()?.foregroundSeconds ?: 1)
        }
        if (uiState.topApps.isEmpty()) {
            item {
                Text("データなし。しばらく使用してから再度確認してください。",
                    modifier = Modifier.padding(32.dp))
            }
        }
    }
}

@Composable
private fun BottomAppsTab(uiState: DashboardUiState, viewModel: DashboardViewModel) {
    val context = LocalContext.current
    var showUninstallDialog by remember { mutableStateOf<AppItem?>(null) }
    var showAlternativesDialog by remember { mutableStateOf<AppItem?>(null) }

    if (uiState.isLoading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(uiState.bottomApps) { app ->
            BottomAppCard(
                app = app,
                onUninstall = { showUninstallDialog = app },
                onAlternatives = {
                    if (app.alternatives.isNotEmpty()) {
                        showAlternativesDialog = app
                    }
                },
            )
        }
    }

    // Uninstall confirmation dialog
    showUninstallDialog?.let { app ->
        UninstallConfirmDialog(
            app = app,
            viewModel = viewModel,
            onDismiss = { showUninstallDialog = null },
            onConfirm = {
                try {
                    val intent = Intent(Intent.ACTION_DELETE).apply {
                        data = Uri.parse("package:${app.packageName}")
                    }
                    context.startActivity(intent)
                    viewModel.logDeletion(app.packageName, app.appName, "least_used", true)
                } catch (e: Exception) {
                    viewModel.logDeletion(app.packageName, app.appName, "least_used", false)
                }
                showUninstallDialog = null
            },
        )
    }

    // Alternatives dialog
    showAlternativesDialog?.let { app ->
        AlternativesDialog(
            app = app,
            onDismiss = { showAlternativesDialog = null },
            onInstall = { alt ->
                if (alt.packageId != null) {
                    try {
                        val intent = Intent(Intent.ACTION_VIEW,
                            Uri.parse("market://details?id=${alt.packageId}"))
                        context.startActivity(intent)
                    } catch (_: android.content.ActivityNotFoundException) {
                        // Play Store not available
                    }
                }
                showAlternativesDialog = null
            },
        )
    }
}

@Composable
private fun AppUsageCard(app: AppItem, showBar: Boolean, maxSeconds: Long) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(app.appName, fontWeight = FontWeight.Medium,
                    modifier = Modifier.weight(1f))
                Text(app.foregroundTime, style = MaterialTheme.typography.bodySmall)
            }
            if (showBar && maxSeconds > 0) {
                Spacer(Modifier.height(4.dp))
                val fraction = (app.foregroundSeconds.toFloat() / maxSeconds).coerceIn(0f, 1f)
                LinearProgressIndicator(
                    progress = { fraction },
                    modifier = Modifier.fillMaxWidth().height(6.dp),
                )
            }
        }
    }
}

@Composable
private fun BottomAppCard(
    app: AppItem,
    onUninstall: () -> Unit,
    onAlternatives: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(app.appName, fontWeight = FontWeight.Medium)
                    Text("使用時間: ${app.foregroundTime}",
                        style = MaterialTheme.typography.bodySmall)
                    if (app.rejectionCount > 0) {
                        Text("見送り: ${app.rejectionCount}回",
                            style = MaterialTheme.typography.bodySmall,
                            color = when {
                                app.rejectionCount > 5 -> MaterialTheme.colorScheme.error
                                app.rejectionCount > 2 -> Color(0xFFFF9800)
                                else -> MaterialTheme.colorScheme.onSurfaceVariant
                            })
                    }
                }
                Row {
                    if (app.alternatives.isNotEmpty()) {
                        TextButton(onClick = onAlternatives) { Text("代替") }
                    }
                    IconButton(onClick = onUninstall) {
                        Icon(Icons.Default.Delete,
                            tint = MaterialTheme.colorScheme.error,
                            contentDescription = "アンインストール")
                    }
                }
            }
        }
    }
}

@Composable
private fun UninstallConfirmDialog(
    app: AppItem,
    viewModel: DashboardViewModel,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
) {
    val warningLevel = when {
        app.rejectionCount > 5 -> "重要警告"
        app.rejectionCount > 2 -> "警告"
        app.rejectionCount > 0 -> "注意"
        else -> "確認"
    }

    val extraMessage = when {
        app.rejectionCount > 5 ->
            "\n\n過去に${app.rejectionCount}回削除を見送っています。" +
            "\n何度も削除候補に挙がっています。今回こそ削除を検討してください。"
        app.rejectionCount > 2 ->
            "\n\n過去に${app.rejectionCount}回削除を見送っています。" +
            "\n本当に必要なアプリか再検討してください。"
        app.rejectionCount > 0 ->
            "\n\n過去に${app.rejectionCount}回削除を見送っています。"
        else -> ""
    }

    AlertDialog(
        onDismissRequest = {
            viewModel.logRejection(app.packageName, app.appName, "first")
            onDismiss()
        },
        title = { Text("アンインストール [$warningLevel]") },
        text = {
            Text(
                "アプリ名: ${app.appName}\n" +
                "使用時間: ${app.foregroundTime}\n" +
                "代替候補: ${app.alternatives.firstOrNull()?.name ?: "なし"}" +
                extraMessage
            )
        },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text("アンインストール", color = MaterialTheme.colorScheme.error)
            }
        },
        dismissButton = {
            TextButton(onClick = {
                viewModel.logRejection(app.packageName, app.appName, "first")
                onDismiss()
            }) {
                Text("キャンセル")
            }
        },
    )
}

@Composable
private fun AlternativesDialog(
    app: AppItem,
    onDismiss: () -> Unit,
    onInstall: (com.apppulse.recommender.Alternative) -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("${app.appName} の代替アプリ") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                app.alternatives.forEach { alt ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        ),
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(alt.name, fontWeight = FontWeight.Medium)
                                Text(alt.reason,
                                    style = MaterialTheme.typography.bodySmall)
                            }
                            if (alt.packageId != null) {
                                TextButton(onClick = { onInstall(alt) }) {
                                    Text("ストア")
                                }
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("閉じる") }
        },
    )
}

@Composable
private fun DeletionLogTab(viewModel: DashboardViewModel) {
    val log by viewModel.deletionLog.collectAsStateWithLifecycle()

    if (log.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("削除履歴はありません")
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(log) { entry ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(entry.appName, fontWeight = FontWeight.Medium)
                        Text("理由: ${entry.reason}",
                            style = MaterialTheme.typography.bodySmall)
                    }
                    Text(
                        if (entry.success) "成功" else "失敗",
                        color = if (entry.success)
                            MaterialTheme.colorScheme.secondary
                        else MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
    }
}
