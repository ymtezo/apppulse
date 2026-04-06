package com.apppulse.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = darkColorScheme(
    primary = androidx.compose.ui.graphics.Color(0xFF89B4FA),
    secondary = androidx.compose.ui.graphics.Color(0xFFA6E3A1),
    tertiary = androidx.compose.ui.graphics.Color(0xFFF38BA8),
    background = androidx.compose.ui.graphics.Color(0xFF1E1E2E),
    surface = androidx.compose.ui.graphics.Color(0xFF313244),
    onPrimary = androidx.compose.ui.graphics.Color(0xFF1E1E2E),
    onBackground = androidx.compose.ui.graphics.Color(0xFFCDD6F4),
    onSurface = androidx.compose.ui.graphics.Color(0xFFCDD6F4),
)

private val LightColorScheme = lightColorScheme(
    primary = androidx.compose.ui.graphics.Color(0xFF1E66F5),
    secondary = androidx.compose.ui.graphics.Color(0xFF40A02B),
    tertiary = androidx.compose.ui.graphics.Color(0xFFD20F39),
)

@Composable
fun AppPulseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context)
            else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content,
    )
}
