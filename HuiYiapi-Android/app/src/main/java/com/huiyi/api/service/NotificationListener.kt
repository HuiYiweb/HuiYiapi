package com.huiyi.api.service
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.huiyi.api.core.network.WebSocketManager
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class NotificationListener : NotificationListenerService() {
    companion object { private const val TAG = "HuiYi_Notif"; var isRunning = false }

    @Inject lateinit var wsManager: WebSocketManager

    override fun onCreate() {
        super.onCreate(); isRunning = true; Log.i(TAG, "通知监听服务已启动")
    }

    override fun onDestroy() {
        super.onDestroy(); isRunning = false
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val packageName = sbn.packageName
        // 只处理目标 IM 应用
        if (packageName !in MONITORED_PACKAGES) return

        val extras = sbn.notification.extras
        val title = extras.getString("android.title") ?: ""
        var content = extras.getCharSequence("android.text")?.toString() ?: ""
        val subText = extras.getCharSequence("android.subText")?.toString() ?: ""
        val summary = extras.getCharSequence("android.summaryText")?.toString() ?: ""

        // 检测群聊（标题为群名，内容含发送者）
        val isGroup = title.isNotEmpty() && content.contains(":") && subText.isNotEmpty()
        val sender = if (isGroup) content.substringBefore(":").trim() else title
        val msgContent = if (isGroup) content.substringAfter(":").trim() else content

        if (msgContent.isBlank()) return

        Log.d(TAG, "[${if (isGroup) "群聊" else "私聊"}] $packageName: $sender -> $msgContent")
        wsManager.sendMessage(packageName, sender, msgContent, isGroup, if (isGroup) title else "")
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {}

    companion object {
        // 默认监听的 IM 包名（可通过配置扩展）
        val MONITORED_PACKAGES = setOf(
            "com.tencent.mm",        // 微信
            "com.tencent.mobileqq",  // QQ
            "org.telegram.messenger", // Telegram
            "com.alibaba.android.rimet", // 钉钉
        )
    }
}
