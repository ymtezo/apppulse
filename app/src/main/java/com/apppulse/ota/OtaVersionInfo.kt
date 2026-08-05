package com.apppulse.ota

import org.json.JSONObject

data class OtaVersionInfo(
    val versionCode: Long,
    val versionName: String,
    val apkUrl: String
) {
    companion object {
        fun fromJson(json: String): OtaVersionInfo {
            val obj = JSONObject(json)
            return OtaVersionInfo(
                versionCode = obj.getLong("version_code"),
                versionName = obj.getString("version_name"),
                apkUrl = obj.getString("apk_url")
            )
        }
    }
}
