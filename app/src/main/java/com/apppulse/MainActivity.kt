package com.apppulse

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.apppulse.ui.screens.DashboardScreen
import com.apppulse.ui.theme.AppPulseTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AppPulseTheme {
                DashboardScreen()
            }
        }
    }
}
