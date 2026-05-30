package com.huiyi.api.service
import android.app.*
import android.content.Intent
import android.os.IBinder
import com.huiyi.api.HuiYiApplication
import com.huiyi.api.core.network.WebSocketManager

class WebSocketKeepAliveService : Service() {
    override fun onCreate() {
        super.onCreate()
        val notif = Notification.Builder(this, HuiYiApplication.CHANNEL_WS)
            .setContentTitle("HuiYi 运行中")
            .setContentText("正在监听消息...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true).build()
        startForeground(HuiYiApplication.NOTIFICATION_ID_WS, notif)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        WebSocketManager.connect()
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        WebSocketManager.disconnect()
        super.onDestroy()
    }
}
