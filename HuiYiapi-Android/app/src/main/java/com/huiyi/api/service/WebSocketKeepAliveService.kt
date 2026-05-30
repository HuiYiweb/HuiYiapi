package com.huiyi.api.service
import android.app.*
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager
import com.huiyi.api.HuiYiApplication
import com.huiyi.api.core.network.WebSocketManager
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class WebSocketKeepAliveService : Service() {
    @Inject lateinit var wsManager: WebSocketManager
    private lateinit var wakeLock: PowerManager.WakeLock

    override fun onCreate() {
        super.onCreate()
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "HuiYi:WSKeepAlive")
        wakeLock.acquire(10 * 60 * 1000L)

        val notif = Notification.Builder(this, HuiYiApplication.CHANNEL_WS)
            .setContentTitle("HuiYi 运行中")
            .setContentText("正在监听消息...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
        startForeground(HuiYiApplication.NOTIFICATION_ID_WS, notif)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        wsManager.connect()
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        wsManager.disconnect()
        if (::wakeLock.isInitialized && wakeLock.isHeld) wakeLock.release()
        super.onDestroy()
    }
}
