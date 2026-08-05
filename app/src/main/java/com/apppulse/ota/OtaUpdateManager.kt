package com.apppulse.ota

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class OtaUpdateManager(private val context: Context) {
    private val tag = "OtaUpdateManager"

    suspend fun checkAndUpdate(versionUrl: String): OtaUpdateResult = withContext(Dispatchers.IO) {
        if (versionUrl.isBlank() || versionUrl == PLACEHOLDER) {
            return@withContext OtaUpdateResult(false, "OTA URL not configured")
        }
        val info = fetchVersionInfo(versionUrl)
            ?: return@withContext OtaUpdateResult(false, "Failed to fetch version info")
        val currentVersion = getCurrentVersionCode()
        if (info.versionCode <= currentVersion) {
            return@withContext OtaUpdateResult(
                false,
                "Already up to date (current=$currentVersion, remote=${info.versionCode})"
            )
        }
        val apk = downloadApk(info.apkUrl)
            ?: return@withContext OtaUpdateResult(false, "Failed to download APK")
        installApk(apk)
        OtaUpdateResult(true, "APK downloaded, install prompt shown")
    }

    private fun getCurrentVersionCode(): Long {
        return try {
            val packageInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.PackageInfoFlags.of(0)
                )
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getPackageInfo(context.packageName, 0)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                packageInfo.longVersionCode
            } else {
                packageInfo.versionCode.toLong()
            }
        } catch (e: Exception) {
            Log.e(tag, "Failed to get version code", e)
            0L
        }
    }

    private fun fetchVersionInfo(versionUrl: String): OtaVersionInfo? {
        return try {
            val connection = (URL(versionUrl).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 15_000
                readTimeout = 15_000
                instanceFollowRedirects = true
                setRequestProperty("Accept", "application/json")
                setRequestProperty("User-Agent", "AppPulse-OTA/${context.packageName}")
            }
            val code = connection.responseCode
            if (code !in 200..299) {
                Log.w(tag, "Version check failed: HTTP $code")
                return null
            }
            val text = connection.inputStream.bufferedReader().use { it.readText() }
            OtaVersionInfo.fromJson(text)
        } catch (e: Exception) {
            Log.e(tag, "Failed to fetch version info", e)
            null
        }
    }

    private fun downloadApk(apkUrl: String): File? {
        if (!apkUrl.startsWith("https://")) {
            Log.w(tag, "APK URL must use HTTPS: $apkUrl")
            return null
        }
        return try {
            val connection = (URL(apkUrl).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 15_000
                readTimeout = 60_000
                instanceFollowRedirects = true
            }
            val code = connection.responseCode
            if (code !in 200..299) {
                Log.w(tag, "APK download failed: HTTP $code")
                return null
            }
            val outputDir = File(context.cacheDir, "updates").apply { mkdirs() }
            val outputFile = File(outputDir, "apppulse-update.apk")
            connection.inputStream.use { input ->
                outputFile.outputStream().use { output -> input.copyTo(output) }
            }
            outputFile
        } catch (e: Exception) {
            Log.e(tag, "Failed to download APK", e)
            null
        }
    }

    private fun installApk(apkFile: File) {
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            apkFile
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(intent)
    }

    companion object {
        const val PLACEHOLDER = "https://example.com/apppulse/version.json"
    }
}

data class OtaUpdateResult(
    val success: Boolean,
    val message: String
)
