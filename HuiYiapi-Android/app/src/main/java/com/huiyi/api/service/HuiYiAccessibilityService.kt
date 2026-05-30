package com.huiyi.api.service
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.huiyi.api.device.DeviceController

class HuiYiAccessibilityService : AccessibilityService() {
    companion object { var instance: HuiYiAccessibilityService? = null; var isRunning = false }

    override fun onCreate() {
        super.onCreate(); instance = this; isRunning = true
        DeviceController.setService(this)
        Log.i("HuiYi_A11y", "无障碍服务已启动")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        serviceInfo = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPES_ALL_MASK
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy(); instance = null; isRunning = false
        DeviceController.setService(null)
    }
}
