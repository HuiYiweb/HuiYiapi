package com.huiyi.api
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class HuiYiApplication : Application() {
    companion object {
        const val CHANNEL_WS = "huiyi_ws_channel"
        const val CHANNEL_CALL = "huiyi_call_channel"
    }
    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val mgr = getSystemService(NotificationManager::class.java)
            mgr.createNotificationChannels(listOf(
                NotificationChannel(CHANNEL_WS, "连接状态", NotificationManager.IMPORTANCE_LOW),
                NotificationChannel(CHANNEL_CALL, "通话处理", NotificationManager.IMPORTANCE_DEFAULT)
            ))
        }
    }
}
