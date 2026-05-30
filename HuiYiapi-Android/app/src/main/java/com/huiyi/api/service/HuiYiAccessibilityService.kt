package com.huiyi.api.service
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.huiyi.api.device.DeviceController
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class HuiYiAccessibilityService : AccessibilityService() {
    companion object { private const val TAG = "HuiYi_A11y"; var instance: HuiYiAccessibilityService? = null; var isRunning = false }

    @Inject lateinit var deviceController: DeviceController

    override fun onCreate() {
        super.onCreate(); instance = this; isRunning = true
        deviceController.setService(this)
        Log.i(TAG, "无障碍服务已启动")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        val info = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPES_ALL_MASK
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_REQUEST_ENHANCED_WEB_ACCESSIBILITY or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }
        serviceInfo = info
        Log.i(TAG, "无障碍服务已配置: ${info.flags}")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() { Log.w(TAG, "无障碍服务被中断") }

    override fun onDestroy() {
        super.onDestroy(); instance = null; isRunning = false
        deviceController.setService(null)
        Log.i(TAG, "无障碍服务已销毁")
    }
}
