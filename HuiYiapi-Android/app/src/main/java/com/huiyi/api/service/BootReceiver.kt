package com.huiyi.api.service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i("HuiYi_Boot", "开机自启，启动 WebSocket 服务")
            // 启动保活服务
            val serviceIntent = Intent(context, WebSocketKeepAliveService::class.java)
            context.startForegroundService(serviceIntent)
        }
    }
}
