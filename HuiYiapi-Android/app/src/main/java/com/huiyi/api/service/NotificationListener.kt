package com.huiyi.api.service
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.huiyi.api.core.network.WebSocketManager

class NotificationListener : NotificationListenerService() {
    companion object {
        var isRunning = false
        val MONITORED_PACKAGES = setOf("com.tencent.mm", "com.tencent.mobileqq", "org.telegram.messenger", "com.alibaba.android.rimet")
    }

    override fun onCreate() { super.onCreate(); isRunning = true; Log.i("HuiYi_Ntf", "通知监听已启动") }

    override fun onDestroy() { super.onDestroy(); isRunning = false }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val pkg = sbn.packageName
        if (pkg !in MONITORED_PACKAGES) return

        val extras = sbn.notification.extras
        val title = extras.getString("android.title") ?: ""
        val content = extras.getCharSequence("android.text")?.toString() ?: ""
        if (content.isBlank()) return

        val isGroup = title.isNotEmpty() && content.contains(":")
        val sender = if (isGroup) content.substringBefore(":").trim() else title
        val msg = if (isGroup) content.substringAfter(":").trim() else content

        Log.d("HuiYi_Ntf", "[${if (isGroup) "群" else "私"}] $sender -> $msg")
        WebSocketManager.sendMessage(pkg, sender, msg, isGroup, if (isGroup) title else "")
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {}
}
